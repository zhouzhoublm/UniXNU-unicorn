# UniXNU-unicorn (English)

[简体中文](README.md) | **English**

UniXNU format 2 device support for the **Xiaomi 12S Pro** (codename **unicorn**, model 2206122SC, Qualcomm **SM8475** / taro).

- Target OS: **iPadOS 18.7.10 / 22H374 / Darwin 24**, the same profile used by `UniXNU-thor` and `UniXNU-pong`.
- Baseline: `zhouzhoublm/UniXNU-unicorn` at `a99b5c1d2128894519948eeee9faa49a7bc58021`.
- Firmware: a separate `uefi-unicorn` tree derived from `uefi-mondrian` with an `unicornPkg` platform.

## Feasibility

**Feasible, with substantial work already done.** The SM8475 SoC layer and the Darwin 24 OS profile are shared with working devices (Redmi K60 / Nothing Phone 2 / Xiaomi 12S Ultra). This board already has 13/13 hardware values measured on the real device, and the UEFI menu, physical keys and payload menu have been observed on hardware. The remaining work is to produce a 22H374 kernel, finish the firmware build, and qualify each XNU subsystem on the device.

See [`docs/FEASIBILITY.md`](docs/FEASIBILITY.md) for the evidence, risk register and phase plan.

## Current status (honest)

| Layer | Status |
| --- | --- |
| Format 2 profile resolution | Done — all four layers resolve |
| Source pins | Done — `unixnu fetch` resolves the 22H374 inputs |
| Hardware DTS | Done — generated from the live device tree, 13/13 facts recorded |
| UEFI menu and physical keys | Done on device (M1/M2) |
| Payload menu | Partial — 4 entries rendered (M3); the old Darwin 22 kernel was rejected by the Darwin 24 loader |
| Kernel build | Blocked — requires macOS/Xcode and an IPSW-derived `volume-layout.json` |
| Final UEFI build | Blocked — depends on the separate `uefi-unicorn` tree |
| XNU, launchd, display, touch, wireless, audio | Not yet qualified on device |

## Key board facts

| Subsystem | unicorn (measured) |
| --- | --- |
| SoC / DRAM | SM8475, 12 GiB at `0x80000000` |
| Panel | `l2s_38_0c_0a_dsc_cmd`, 1440x3200, DSC 10bpc, LTPO 120 Hz |
| Touch | FocalTech FTS, SPI `0x990000`, IRQ GPIO 21, reset GPIO 20 |
| Keys | Power = PON PPID `0x13`; volume up = TLMM GPIO 6 |
| UFS | `1d84000.ufshc`, SPI 265, SMMU SID `0xe0`, 2 lanes |
| Wi-Fi | QCA6490, PCIe RC0 `0x1c00000`, wlan-en GPIO 80 |
| GPU | Adreno 730 v3 |
| userdata | 4K LBA `3013120..61731834`, 64 GiB tail window |

## Documentation

- [`docs/FEASIBILITY.md`](docs/FEASIBILITY.md) — feasibility, risks, phases, source pins.
- [`docs/BINDING-PLAN.md`](docs/BINDING-PLAN.md) — which board values must replace the donor device's values.
- [`docs/BUILD-RUNBOOK.md`](docs/BUILD-RUNBOOK.md) — collection, build, image assembly, boot and acceptance.
- [`docs/OFFLINE-VALIDATION.md`](docs/OFFLINE-VALIDATION.md) — reproducible offline consistency report.
- [`docs/HARDWARE-FACTS.md`](docs/HARDWARE-FACTS.md) — measured hardware inventory with sources.
- [`porting.toml`](porting.toml) — structured porting record.

## Build

```bash
bash scripts/collect-device.sh --output ../evidence/unicorn-$(date +%Y%m%d)  # read-only
python3 scripts/validate-offline.py                                        # no Mac/device needed
bash scripts/bootstrap-unicorn.sh --unixnu ../UniXNU --soc ../soc-seed
python3.12 scripts/build-pong-format2.py --unixnu ../UniXNU --out ../build \
        --jobs 4 --defconfig unicorn_ipados18_defconfig
```

Kernel and payload builds require Xcode, Apple open-source dependencies, an iPadOS 18.7.10 IPSW and board-specific firmware. With no Mac, use `.github/workflows/package.yml` on a `macos-15-intel` runner.

## Safety rules

1. Bring-up uses `fastboot boot` only — images live in RAM; no partition is flashed.
2. Never run `fastboot flash persist` or `fastboot flash all`: TEE keys can be destroyed permanently.
3. UniXNU windows occupy the last 64 GiB of `userdata`. Shrink Android's data filesystem and verify the GPT before installing anything.
4. Back up and explicitly confirm any target partition before a write operation.

## License

Board-level code is BSD-2-Clause-Patent. Imported components keep their SPDX identifiers and original licences; see `THIRD_PARTY_NOTICES.md`.
