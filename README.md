# UniXNU-unicorn

小米 12S Pro（**unicorn**，型号 2206122SC，高通 **SM8475** / taro）的 UniXNU 设备仓，格式 2（`schema_version = 2`）。

- 目标系统：**iPadOS 18.7.10 / 22H374 / darwin24**（与 `UniXNU-thor`、`UniXNU-pong` 同路线）
- 基线来源：`zhouzhoublm/UniXNU-unicorn`，pin `a99b5c1d2128894519948eeee9faa49a7bc58021`
- 模板来源：`SFZ97/UniXNU-thor`（小米 12S Ultra，同 SoC）
- 配套固件：`uefi-unicorn`（由 `uefi-mondrian` 派生 + `unicornPkg`）

## 可行性结论

**可行，且已有真机基础。** 同 SoC 的 mondrian/pong/thor 提供了可复用的 SM8475 与 darwin24 层；本机 13/13 板级数值已实测，UEFI 菜单、实体键、payload 清单渲染已在真机出现。剩余工作是补齐 22H374 内核产物、固件最终构建与 XNU 阶段逐项验收。详见 [`docs/FEASIBILITY.md`](docs/FEASIBILITY.md)。

## 当前状态（诚实版）

| 层 | 状态 |
| --- | --- |
| 格式 2 配置解析 | ✅ 四层 profile 全解析 |
| 源码获取 | ✅ `unixnu fetch` 的 pin 全部到位（xnu `43a90889` / 22H374） |
| 硬件 DTS | ✅ 本机 live DT 生成，13/13 项实测登记 |
| UEFI 上屏 + 菜单 + 实体键 | ✅ 真机 M1/M2，见 `docs/evidence/m1-menu.md` |
| payload 清单装载 | ◐ M3 已显示 4 个启动项；旧 darwin22 内核被 darwin24 装载器拒绝 |
| 内核构建 | ⛔ 缺 macOS/Xcode 与由 IPSW 生成的 `volume-layout.json` |
| UEFI 最终构建 | ⛔ 依赖独立的 `uefi-unicorn` 固件树 |
| XNU / launchd / 显示 / 触摸 / 无线 / 音频 | ⛔ 均未上机验证 |

## 文档入口

| 文档 | 内容 |
| --- | --- |
| [`docs/FEASIBILITY.md`](docs/FEASIBILITY.md) | 可行性、风险分级、阶段计划、参考 pin |
| [`docs/BINDING-PLAN.md`](docs/BINDING-PLAN.md) | 板级差异绑定矩阵：哪些能继承、哪些必须替换 |
| [`docs/BUILD-RUNBOOK.md`](docs/BUILD-RUNBOOK.md) | 采集、构建、组装、上机、验收与红线 |
| [`docs/OFFLINE-VALIDATION.md`](docs/OFFLINE-VALIDATION.md) | 本机离线一致性校验结果 |
| [`docs/HARDWARE-FACTS.md`](docs/HARDWARE-FACTS.md) | 13 项本机实测硬件事实与出处 |
| [`porting.toml`](porting.toml) | 结构化移植记录（14 子系统） |

## 板级事实摘要

| 子系统 | unicorn 实测 |
| --- | --- |
| SoC / DRAM | SM8475，12 GiB @ `0x80000000` |
| 面板 | `l2s_38_0c_0a_dsc_cmd`，1440×3200，DSC 10bpc，LTPO 120 Hz |
| 触摸 | FocalTech FTS，SPI `0x990000`，IRQ GPIO 21 / RST GPIO 20 |
| 按键 | 电源 PON PPID `0x13`；音量上 TLMM GPIO 6 |
| UFS | `1d84000.ufshc`，SPI 265，SMMU SID `0xe0`，2 lane |
| Wi-Fi | QCA6490，PCIe RC0 `0x1c00000`，wlan-en GPIO 80 |
| GPU | Adreno 730 v3 |
| userdata | 4K LBA `3013120…61731834`，尾部 64 GiB 窗口 |

## 构建

```bash
# 1. 只读硬件采集（需要 root + adb）
bash scripts/collect-device.sh --output ../evidence/unicorn-$(date +%Y%m%d)

# 2. 离线一致性校验（不需要 macOS / 真机）
python3 scripts/validate-offline.py

# 3. 解析四层配置（需要 ../UniXNU 与 ../soc-seed）
bash scripts/bootstrap-unicorn.sh --unixnu ../UniXNU --soc ../soc-seed
python3.12 scripts/build-pong-format2.py --unixnu ../UniXNU --out ../build \
        --jobs 4 --defconfig unicorn_ipados18_defconfig

# 4. 内核 / payload / 镜像 / 上机
#    见 docs/BUILD-RUNBOOK.md
```

内核编译需要完整 Xcode、Apple 开源依赖、22H374 的 IPSW 与本机私有固件；没有 Mac 时走 `.github/workflows/package.yml`。

## 数据安全红线

- 上机一律 `fastboot boot`（RAM 临时引导），**不 flash 任何分区**。
- **禁止** `fastboot flash persist` / `flash all`（TEE 密钥不可逆损坏）。
- UniXNU 窗口放在 userdata 尾部 64 GiB；安装前必须先收缩安卓 data（`board.toml [userdata]` 里的 `TODO(resize)`）。
- 任何写设备操作前先备份并明确确认目标分区。

## 许可

设备级代码 BSD-2-Clause-Patent；导入组件保留各自 SPDX 与许可证，见 `THIRD_PARTY_NOTICES.md`。
