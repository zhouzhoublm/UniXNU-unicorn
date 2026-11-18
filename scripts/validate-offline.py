#!/usr/bin/env python3
"""Offline consistency checks for the UniXNU-unicorn device repository.

Runs on Windows/Linux/macOS with Python 3.11+ and no device, Xcode or IPSW.
It checks what can be checked without a build toolchain, then writes a Markdown
report so the result is reviewable evidence rather than terminal output.

Usage:
    python3 scripts/validate-offline.py
    python3 scripts/validate-offline.py --json out.json --md docs/OFFLINE-VALIDATION.md
"""
from __future__ import annotations

import argparse
import json
import re
import tomllib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINDINGS: list[dict[str, str]] = []


def add(level: str, check: str, message: str) -> None:
    FINDINGS.append({"level": level, "check": check, "message": message})


def read_text(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def load_toml(rel: str) -> dict:
    p = ROOT / rel
    if not p.is_file():
        add("ERROR", "file", f"missing {rel}")
        return {}
    try:
        return tomllib.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        add("ERROR", "toml", f"{rel} is not valid TOML: {exc}")
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", type=Path, default=ROOT / "offline-validation.json")
    ap.add_argument("--md", type=Path, default=ROOT / "docs" / "OFFLINE-VALIDATION.md")
    args = ap.parse_args()

    board = load_toml("board.toml")
    porting = load_toml("porting.toml")
    feeds = load_toml("feeds.toml")
    facts_path = ROOT / "verified-facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8")) if facts_path.is_file() else {}
    dts = read_text("dts/unicorn.dts")
    defconfig = read_text("configs/unicorn_ipados18_defconfig")
    readme = read_text("README.md")
    readme_en = read_text("README_EN.md")

    b = board.get("board", {})
    # -- identity -----------------------------------------------------------
    if board.get("schema_version") == 2:
        add("PASS", "schema", "board.toml uses format 2 (schema_version = 2)")
    else:
        add("ERROR", "schema", "board.toml must use schema_version = 2")
    for key, expected in (("name", "unicorn"), ("soc", "SM8475"),
                          ("soc_source", "sm8475"),
                          ("os_profile", "ipados-18.7.10-22H374")):
        got = b.get(key)
        add("PASS" if got == expected else "ERROR", "identity",
            f"board.{key} = {got!r} (expected {expected!r})")
    dt = board.get("device_tree", {})
    if dt.get("source") != "device:dts/unicorn.dts":
        add("ERROR", "dts", "device_tree.source must point at device:dts/unicorn.dts")

    # -- userdata geometry --------------------------------------------------
    ud = board.get("userdata", {})
    first, last = ud.get("first_lba"), ud.get("last_lba")
    if isinstance(first, int) and isinstance(last, int):
        blocks = last - first + 1
        gib = blocks * ud.get("lba_bytes", 4096) / 1024**3
        if abs(gib - 64) < 0.01:
            add("PASS", "userdata", f"OS/SystemOS/Data window is {gib:.0f} GiB at the tail of userdata")
        else:
            add("WARN", "userdata", f"window is {gib:.2f} GiB, expected 64 GiB")
        if last > 0x3ADF3FA:
            add("ERROR", "userdata", f"last_lba {last} exceeds the measured device end 0x3ADF3FA")
        # Guard against the literal/decimal mismatch found on 2026-11-18:
        # 0x2AE13BB/0x3AE1F7A are NOT the measured 44954619/61731834.
        if (first, last) != (44954619, 61731834):
            add("ERROR", "userdata",
                f"first_lba/last_lba = {first}/{last}; expected the measured 44954619/61731834 "
                "(0x2ADF3FB/0x3ADF3FA)")
    else:
        add("ERROR", "userdata", "first_lba/last_lba missing")

    # -- local hardware facts ----------------------------------------------
    verified = facts.get("verified", {})
    add("PASS" if len(verified) == 13 else "WARN", "facts",
        f"verified-facts.json contains {len(verified)} measured values (reference: 13)")
    expected_tokens = {
        "dts.dram_size": "12 GiB",
        "dts.ufs_spi": "265",
        "dts.ufs_smmu_sid": "0xe0",
        "dts.pon_ppid": "0x13",
        "dts.touch_compatible": "FocalTech",
        "adt.owned_memory_size": "4 GiB",
    }
    for key, token in expected_tokens.items():
        value = str(verified.get(key, ""))
        add("PASS" if token.lower() in value.lower() else "WARN", "facts",
            f"{key}: {'contains' if token.lower() in value.lower() else 'missing'} {token!r}")

    # -- board DTS token cross-check ---------------------------------------
    dts_tokens = {
        "12 GiB DRAM base": "0x80000000",
        "touch SPI base": "0x990000",
        "touch IRQ GPIO 21": "irq-gpio-num = <21>",
        "touch RST GPIO 20": "reset-gpio-num = <20>",
        "PON PPID 0x13": "pon-ppid = <0x13>",
        "volume-up GPIO 6": "volume-up-gpio-num = <6>",
        "UFS SMMU SID": "pong,smmu-stream-id = <0xe0>",
        "UFS SPI 265": "pong,ufs-spi = <265>",
        "QCA6490 PCIe RC0": "0x1c00000",
    }
    for label, token in dts_tokens.items():
        add("PASS" if token in dts else "ERROR", "dts", f"{label}: {'found' if token in dts else 'NOT found'}")

    m = re.search(r"max-x\s*=\s*<(\d+)>", dts)
    n = re.search(r"max-y\s*=\s*<(\d+)>", dts)
    if m and n and (int(m.group(1)), int(n.group(1))) != (14400, 32000):
        add("WARN", "touch", f"DTS declares max-x/max-y = {m.group(1)}/{n.group(1)}; "
            "the live FTS axis contract is 14400x32000 (10x fixed point). "
            "Keep panel pixels for UI, raw axes for the driver.")
    else:
        add("PASS", "touch", "DTS touch axes match the measured raw 14400x32000 contract")

    reserved = len(re.findall(r"^\s{8}[A-Za-z0-9_]+@[0-9a-f]+ \{ reg =", dts, re.M))
    if reserved and reserved != 38:
        add("WARN", "memory", f"DTS has {reserved} reserved-memory entries; "
            "HARDWARE-FACTS.md reports 38 from the live device")
    elif reserved:
        add("PASS", "memory", "DTS carries all 38 measured reserved-memory entries")

    todo = len(re.findall(r"TODO\(verify\)", dts))
    add("WARN" if todo else "PASS", "inheritance",
        f"{todo} inherited (unmeasured) values remain in dts/unicorn.dts; "
        "each must be closed with a device dump before enabling the matching driver")

    # -- defconfig and patch wiring ----------------------------------------
    required_config = {
        "CONFIG_XNU_ARMCPU=y": "SM8475 GIC+timer interrupt provider",
        "CONFIG_XNU_NATIVE_UFS=y": "native UFS root",
        "CONFIG_XNU_ARM_DT_PLATFORM=y": "Apple-format device tree platform expert",
    }
    for token, why in required_config.items():
        add("PASS" if token in defconfig else "ERROR", "defconfig", f"{token} ({why})")

    kernel = board.get("kernel", {})
    for series in dict.fromkeys(kernel.get("patch_series", [])):
        label = series
        rel = series.split(":", 1)[-1] if ":" in series else series
        p = ROOT / rel
        add("PASS" if p.is_file() else "ERROR", "patches",
            f"patch series {label}: {'present' if p.is_file() else 'MISSING'}")

    # -- documentation and referenced scripts ------------------------------
    if not readme_en.startswith("# UniXNU-unicorn"):
        add("ERROR", "docs", "README_EN.md is still the stale Pong document")
    else:
        add("PASS", "docs", "README_EN.md describes unicorn")
    stale_hex = []
    # FEASIBILITY.md and BINDING-PLAN.md deliberately quote the stale literals
    # when explaining the defect; check only active configuration and runbook text.
    for rel in ("board.toml", "verified-facts.json", "porting.toml",
                "README.md", "README_EN.md", "docs/BUILD-RUNBOOK.md"):
        text = read_text(rel)
        if "0x2AE13BB" in text or "0x3AE1F7A" in text:
            stale_hex.append(rel)
    add("ERROR" if stale_hex else "PASS", "lba-regression",
        "stale wrong LBA literals in " + ", ".join(stale_hex) if stale_hex
        else "no stale LBA literals in active configuration and docs")

    for rel in ("docs/FEASIBILITY.md", "docs/BINDING-PLAN.md", "docs/BUILD-RUNBOOK.md",
                "scripts/collect-device.sh", "scripts/boot-observe.ps1"):
        p = ROOT / rel
        add("PASS" if p.is_file() else "ERROR", "deliverable",
            f"{rel}: {'present' if p.is_file() else 'MISSING'}")

    referenced = set(re.findall(r"scripts/([A-Za-z0-9_.-]+)", readme + readme_en))
    for name in sorted(referenced):
        if not (ROOT / "scripts" / name).exists():
            add("WARN", "docs", f"README references missing scripts/{name}")

    areas = porting.get("area", []) if isinstance(porting.get("area"), list) else []
    status_count: dict[str, int] = {}
    for area in areas:
        status_count[area.get("status", "unknown")] = status_count.get(area.get("status", "unknown"), 0) + 1
    add("INFO", "record", f"porting.toml tracks {len(areas)} areas: "
        + ", ".join(f"{k}={v}" for k, v in sorted(status_count.items())))

    errors = [f for f in FINDINGS if f["level"] == "ERROR"]
    warns = [f for f in FINDINGS if f["level"] == "WARN"]

    md = [
        "# 离线一致性校验报告",
        "",
        f"生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        "本报告只覆盖**不依赖真机、macOS/Xcode、IPSW 或私有固件**的检查。",
        "任何 PASS 都不代表内核已编译或功能已在本机验证。",
        "",
        f"结论：**{len(errors)} 项错误 / {len(warns)} 项警告 / "
        f"{len(FINDINGS) - len(errors) - len(warns)} 项通过**",
        "",
        "| 级别 | 检查 | 结果 |",
        "| --- | --- | --- |",
    ]
    for f in FINDINGS:
        md.append(f"| {f['level']} | `{f['check']}` | {f['message']} |")
    md += [
        "",
        "## 解读",
        "",
        "- ERROR 必须在进入构建前修掉。",
        "- WARN 是已知的未闭合证据或板级差异，按 `docs/BINDING-PLAN.md` 逐条关闭。",
        "- 内核编译、payload 打包、UEFI 固件与上机验证只能按 `docs/BUILD-RUNBOOK.md` "
        "在具备 macOS/Xcode 与真机的环境执行。",
        "",
    ]
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.md.write_text("\n".join(md), encoding="utf-8")
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps({"generated": datetime.now().astimezone().isoformat(),
                                     "summary": {"error": len(errors), "warn": len(warns),
                                                 "pass": len(FINDINGS) - len(errors) - len(warns)},
                                     "findings": FINDINGS}, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    print(f"{len(errors)} error(s), {len(warns)} warning(s); report: {args.md}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
