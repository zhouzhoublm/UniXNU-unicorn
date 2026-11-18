#!/usr/bin/env bash
# Read-only hardware evidence collector for Xiaomi 12S Pro (unicorn / SM8475).
#
# This script NEVER writes to the device. It only runs adb read commands and
# stores their output on the host. Keep the resulting directory next to the
# device repository so porting.toml evidence can reference it.
#
# Usage:
#   bash scripts/collect-device.sh [--serial <id>] [--output <dir>] [--fastboot]
set -uo pipefail

OUT="$(pwd)/data/unicorn-collect-$(date +%Y%m%d-%H%M%S)"
SERIAL=""
DO_FASTBOOT=0

while [ $# -gt 0 ]; do
  case "$1" in
    --serial)   SERIAL="$2"; shift 2 ;;
    --output)   OUT="$2"; shift 2 ;;
    --fastboot) DO_FASTBOOT=1; shift ;;
    -h|--help)  sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

command -v adb >/dev/null 2>&1 || { echo "adb not found in PATH" >&2; exit 1; }
ADB=(adb)
[ -n "$SERIAL" ] && ADB+=( -s "$SERIAL" )

STATE=$("${ADB[@]}" get-state 2>/dev/null || true)
[ "$STATE" = "device" ] || { echo "device not in adb state 'device' (got: ${STATE:-none})" >&2; exit 1; }

ROOT=0
if [ "$("${ADB[@]}" shell id -u 2>/dev/null | tr -d '\r')" = "0" ]; then
  ROOT=1
elif "${ADB[@]}" shell 'su -c id -u' 2>/dev/null | tr -d '\r' | grep -q '^0$'; then
  ROOT=1
fi
if [ "$ROOT" -ne 1 ]; then
  echo "WARNING: no root shell; several hardware dumps will be incomplete." >&2
fi

run() { # run <output-file> <shell-command>
  local f="$1"; shift
  if [ "$ROOT" -eq 1 ]; then
    "${ADB[@]}" exec-out su -c "$*" >"$f" 2>/dev/null
  else
    "${ADB[@]}" exec-out "$*" >"$f" 2>/dev/null
  fi
}

mkdir -p "$OUT"/{props,memory,dt,block,input,display,wireless,power,boot}

echo "== identity and properties"
run "$OUT/props/getprop.txt" 'getprop'
run "$OUT/props/build-prop.txt" 'cat /system/build.prop'
run "$OUT/props/board-platform.txt" 'getprop ro.board.platform; getprop ro.product.device; getprop ro.product.model; getprop ro.boot.hardware.sku; getprop ro.boot.slot_suffix; getprop ro.boot.verifiedbootstate'

echo "== memory map"
run "$OUT/memory/meminfo.txt" 'cat /proc/meminfo'
run "$OUT/memory/iomem.txt" 'cat /proc/iomem'
run "$OUT/memory/partitions.txt" 'cat /proc/partitions'

echo "== device tree (binary FDT, keep as-is)"
run "$OUT/dt/live-fdt.dtb" 'cat /sys/firmware/fdt'
run "$OUT/dt/model.txt" 'cat /proc/device-tree/model'
run "$OUT/dt/ddr-size.txt" 'cat /proc/device-tree/ddr_size'
run "$OUT/dt/chosen-bootargs.txt" 'cat /proc/device-tree/chosen/bootargs'
run "$OUT/dt/reserved-memory.txt" 'ls -l /proc/device-tree/reserved-memory/'
run "$OUT/boot/cmdline.txt" 'cat /proc/cmdline'

echo "== storage geometry"
run "$OUT/block/by-name.txt" 'ls -l /dev/block/by-name/'
run "$OUT/block/sda-queue.txt" 'cat /sys/block/sda/queue/logical_block_size; cat /sys/block/sda/queue/physical_block_size; cat /sys/block/sda/size'
for part in sda36 sda28 sde14 sde18 sde25 sda21; do
  run "$OUT/block/${part}.txt" "cat /sys/block/sda/${part}/start /sys/block/sda/${part}/size"
done
run "$OUT/block/mount-points.txt" 'cat /proc/mounts'

echo "== input / keys / touch"
run "$OUT/input/devices.txt" 'cat /proc/bus/input/devices'
run "$OUT/input/fts-node.txt" 'ls -l /proc/device-tree/soc/spi@990000/ 2>/dev/null; find /proc/device-tree -name "*fts*" -o -name "*touch*" 2>/dev/null | head -40'
run "$OUT/input/gpio-keys.txt" 'find /proc/device-tree -name "gpio_keys" -o -name "pwrkey" -o -name "pmic_resin" 2>/dev/null | head -40'
run "$OUT/input/getevent.txt" 'getevent -il 2>/dev/null | head -200'

echo "== display"
run "$OUT/display/dumpsys.txt" 'dumpsys display 2>/dev/null | head -300'
run "$OUT/display/drm.txt" 'ls -l /sys/class/drm/ 2>/dev/null; cat /sys/class/drm/card0/*/modes 2>/dev/null | head -40'
run "$OUT/display/panel-dt.txt" 'find /proc/device-tree -name "*dsi*" -o -name "*panel*" 2>/dev/null | head -60'

echo "== wireless"
run "$OUT/wireless/dmesg-qca.txt" 'dmesg 2>/dev/null | grep -iE "qca6490|ath11k|wlan|bluetooth" | tail -200'
run "$OUT/wireless/cnss-dt.txt" 'find /proc/device-tree -name "*cnss*" -o -name "*qca6490*" 2>/dev/null | head -40'

echo "== power / audio / misc"
run "$OUT/power/battery.txt" 'dumpsys battery 2>/dev/null'
run "$OUT/power/power-supply.txt" 'ls -l /sys/class/power_supply/ 2>/dev/null'
run "$OUT/properties-audio.txt" 'cat /proc/asound/cards 2>/dev/null; dmesg 2>/dev/null | grep -iE "wcd938|waipio|lpass" | tail -80'

[ "$DO_FASTBOOT" -eq 1 ] && {
  echo "== fastboot variables (run with the device in fastboot mode)"
  command -v fastboot >/dev/null 2>&1 && {
    F="$OUT/boot/fastboot-getvar-all.txt"
    [ -n "$SERIAL" ] && fastboot -s "$SERIAL" getvar all >"$F" 2>&1 || fastboot getvar all >"$F" 2>&1
  } || echo "fastboot not found; skipped" >&2
}

python3 - "$OUT" <<'PY' || true
import hashlib, pathlib, sys, datetime
root = pathlib.Path(sys.argv[1])
rows = []
for f in sorted(root.rglob('*')):
    if f.is_file():
        rows.append((str(f.relative_to(root)), f.stat().st_size,
                     hashlib.sha256(f.read_bytes()).hexdigest()))
(root / 'MANIFEST.tsv').write_text(
    '# collected ' + datetime.datetime.now().isoformat(timespec='seconds') + '\n'
    + 'path\tsize\tsha256\n' + ''.join('\t'.join(map(str, r)) + '\n' for r in rows))
print(f'collected {len(rows)} files')
PY

echo
echo "Evidence directory: $OUT"
echo "Next: bash scripts/audit-inherited-values.py --help"
echo "Remember: no partition was written. Never run 'fastboot flash' during bring-up."
