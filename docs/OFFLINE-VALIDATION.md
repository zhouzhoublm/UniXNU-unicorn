# 离线一致性校验报告

生成时间：2026-11-18T14:16:38+08:00

本报告只覆盖**不依赖真机、macOS/Xcode、IPSW 或私有固件**的检查。
任何 PASS 都不代表内核已编译或功能已在本机验证。

结论：**0 项错误 / 1 项警告 / 39 项通过**

| 级别 | 检查 | 结果 |
| --- | --- | --- |
| PASS | `schema` | board.toml uses format 2 (schema_version = 2) |
| PASS | `identity` | board.name = 'unicorn' (expected 'unicorn') |
| PASS | `identity` | board.soc = 'SM8475' (expected 'SM8475') |
| PASS | `identity` | board.soc_source = 'sm8475' (expected 'sm8475') |
| PASS | `identity` | board.os_profile = 'ipados-18.7.10-22H374' (expected 'ipados-18.7.10-22H374') |
| PASS | `userdata` | OS/SystemOS/Data window is 64 GiB at the tail of userdata |
| PASS | `facts` | verified-facts.json contains 13 measured values (reference: 13) |
| PASS | `facts` | dts.dram_size: contains '12 GiB' |
| PASS | `facts` | dts.ufs_spi: contains '265' |
| PASS | `facts` | dts.ufs_smmu_sid: contains '0xe0' |
| PASS | `facts` | dts.pon_ppid: contains '0x13' |
| PASS | `facts` | dts.touch_compatible: contains 'FocalTech' |
| PASS | `facts` | adt.owned_memory_size: contains '4 GiB' |
| PASS | `dts` | 12 GiB DRAM base: found |
| PASS | `dts` | touch SPI base: found |
| PASS | `dts` | touch IRQ GPIO 21: found |
| PASS | `dts` | touch RST GPIO 20: found |
| PASS | `dts` | PON PPID 0x13: found |
| PASS | `dts` | volume-up GPIO 6: found |
| PASS | `dts` | UFS SMMU SID: found |
| PASS | `dts` | UFS SPI 265: found |
| PASS | `dts` | QCA6490 PCIe RC0: found |
| WARN | `touch` | DTS declares max-x/max-y = 1440/3200; the live FTS axis contract is 14400x32000 (10x fixed point). Keep panel pixels for UI, raw axes for the driver. |
| PASS | `memory` | DTS carries all 38 measured reserved-memory entries |
| PASS | `inheritance` | 0 inherited (unmeasured) values remain in dts/unicorn.dts; each must be closed with a device dump before enabling the matching driver |
| PASS | `defconfig` | CONFIG_XNU_ARMCPU=y (SM8475 GIC+timer interrupt provider) |
| PASS | `defconfig` | CONFIG_XNU_NATIVE_UFS=y (native UFS root) |
| PASS | `defconfig` | CONFIG_XNU_ARM_DT_PLATFORM=y (Apple-format device tree platform expert) |
| PASS | `patches` | patch series device:migration/format2/arch-darwin24.series: present |
| PASS | `patches` | patch series soc:patches/xnu/series: present |
| PASS | `patches` | patch series os:patches/xnu/series: present |
| PASS | `patches` | patch series device:patches/xnu-ipados18/series: present |
| PASS | `docs` | README_EN.md describes unicorn |
| PASS | `lba-regression` | no stale LBA literals in active configuration and docs |
| PASS | `deliverable` | docs/FEASIBILITY.md: present |
| PASS | `deliverable` | docs/BINDING-PLAN.md: present |
| PASS | `deliverable` | docs/BUILD-RUNBOOK.md: present |
| PASS | `deliverable` | scripts/collect-device.sh: present |
| PASS | `deliverable` | scripts/boot-observe.ps1: present |
| INFO | `record` | porting.toml tracks 14 areas: device-verified=2, implemented=4, planned=7, verified=1 |

## 解读

- ERROR 必须在进入构建前修掉。
- WARN 是已知的未闭合证据或板级差异，按 `docs/BINDING-PLAN.md` 逐条关闭。
- 内核编译、payload 打包、UEFI 固件与上机验证只能按 `docs/BUILD-RUNBOOK.md` 在具备 macOS/Xcode 与真机的环境执行。
