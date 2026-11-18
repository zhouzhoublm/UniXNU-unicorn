# UniXNU-unicorn 未完成项

本文件只列**仍未闭合**的工作。已完成项保留在 `docs/evidence/` 与 `porting.toml` 里作为证据，不再重复勾选。

更新：2026-11-18。完整计划见 [`docs/FEASIBILITY.md`](docs/FEASIBILITY.md)、[`docs/BINDING-PLAN.md`](docs/BINDING-PLAN.md)、[`docs/BUILD-RUNBOOK.md`](docs/BUILD-RUNBOOK.md)。

## M0 硬件事实 — 已完成

- [x] `dts/unicorn.dts`：12 GiB 内存、保留区、UFS、PCIe、按键 PPID、触摸节点已从本机 live DT 替换。
- [x] `board.toml [userdata]`：`first_lba` / `last_lba` 已按本机 `/sys/block/sda/sda36` 换算（窗口仍是规划值，见下方阻塞项）。
- [x] `verified-facts.json`：13/13 项本机实测登记完成。
- [x] 补齐 `scripts/collect-device.sh`：只读采集，生成带 sha256 的 MANIFEST。

## M1–M3 真机已验证

- [x] M1/M2：UEFI 上屏、菜单渲染、音量键与电源键可用（`docs/evidence/m1-menu.md`）。
- [x] M3：payload 清单渲染出 4 个启动项（`docs/evidence/m3-payload-menu.md`）。
- [x] 补齐 `scripts/boot-observe.ps1`：用 USB VID/PID 判定固件状态，避免 `adb devices` 幽灵设备误判。

## 本地构建树 — 已完成（2026-11-18）

- [x] 固定版本框架源码：`D:/UniXNU/framework-pin`，pin `0fc0fc1f9ddd0fbd4787738afef38667df5e0a95`（与 `migration/format2/migration-state.json` 一致）。
- [x] 确定性 SM8475 `soc-seed`：HEAD `a107f6ae646b997086fa1dd1c8ddee0e0d8b5b21`，与 `soc_revision` 校验一致；`audit-inherited-values.py` 13/13 OK。
- [x] 22H374 profile 已装入框架仓；`local.toml` 只含 soc/kit/refer 的本地覆盖。
- [x] 5 个 Apple 参考源码按 `feeds.toml` 的 commit pin 拉取到 `refer/ipados18/`（xnu/libplatform/libdispatch/AvailabilityVersions/IOStorageFamily）。
- [x] 框架 19 个内核子模块按 pin 拉取；`unixnu status` 解析成功，`tree` 已组装到 `framework-pin/out/unicorn/ipados-18.7.10-22H374/unicorn_ipados18/tree`（Windows 上跳过需要 git 的 submodule 步骤，树本身等价）。
- [x] Android Platform Tools：`D:/UniXNU/tools/platform-tools/`（adb 37.0.1 / fastboot 2.4M）；IPSW URL HEAD 200，Content-Length 7,891,396,130 字节（约 7.35 GiB）。
- [x] 固件仓 `D:/UniXNU/uefi-unicorn`（`zhouzhoublm/uefi-unicorn` @ master `2a128a83`）已拉取，含 `Platforms/Xiaomi/unicornPkg`。

## 本机取证 — 已完成（2026-11-18，用户设备 5f6d7677）

- [x] 只读采集（无 root）+ fastboot getvar all：证据在 `docs/evidence/unit-20261118.md`，原始数据 `D:/UniXNU/evidence/unicorn-20261118/`（带 MANIFEST）。
- [x] BL 解锁已确认（orange / unlocked:yes）——bring-up 前置条件满足。
- [x] 面板 1440×3200 LTPO 24–120Hz、`fts` 触摸、`pmic_pwrkey`+`gpio-keys`、`waipio-mtp-snd-card` 全部与声明一致。
- [x] userdata 几何自洽：分区 223.99 GiB = 58,718,715 LBA@4K；尾部窗口恰为 64 GiB 整。
- [x] cpuid 实测 `0x0000043bba5846c1`；`UNIXNU_UNIQUE_CHIP_ID` 建议 = 低 32 位 `ba5846c1`（推断，CI 首跑核对）。
- [x] 深层复核（KSU root，同日）：live FDT/iomem/cmdline 全到手；userdata last_lba `0x3ADF3FA` **逐位一致**，UFS stream-id 0xe0、SPI 265、PON PPID 0x13(pmk8350)、触摸 GPIO 21、PCIe @1c00000 全部实测吻合（`docs/evidence/unit-20261118.md`）。
- [x] reserved-memory 对账：live 55 段 vs DTS 38 段——被排除 17 段均为 Android 动态分配或已被 MemoryMapLib 覆盖（splash/QTEE/ramoops），排除安全；DTS 两个 `TODO(verify)` 已关闭。
- [x] 修正描述笔误：PON 是 pmk8350（非 pm8998），PPID 0x13 不变。

## 当前阻塞（必须先解决）

- [ ] `volume-layout.json`：需要 macOS + 合法获取的 iPadOS 18.7.10 / 22H374 IPSW 生成 APFS 卷布局；三个卷 UUID 会编进内核常量。IPSW URL 已核验可达，但本环境无 macOS 无法解包。
- [ ] 22H374 的 `kernel.macho` + `payload.img`：M3 里用的是 darwin22 内核，darwin24 装载器拒绝；拿到 22H374 产物后重打镜像。
- [ ] `uefi-unicorn` 最终固件：已补齐 EDK2/Mu/Binaries/openssl 源码（原仓这 6 个子模块是指向 `/root/uefi-unicorn/...` 的失效符号链接，已替换为上游源码）；编译仍需 macOS/Linux + stuart_build，本环境不能产出 `.fd`。
- [ ] `UNIXNU_UNIQUE_CHIP_ID`：本机平台种子，只能作为 CI secret 提供，不进公开源码。

## 板级差异待关闭（按 `docs/BINDING-PLAN.md`）

- [ ] FocalTech FTS 触摸驱动：DTS 节点目前 `status="disabled"`；原始轴 14400×32000 与面板像素 1440×3200 要分清。
- [x] reserved-memory 条目数：DTS 与 `docs/HARDWARE-FACTS.md` 均为 38 段，离线校验器已实测确认；UEFI 内存描述符仍待 M3 后收敛。
- [x] `dts/unicorn.dts` 里 `TODO(verify)` 的继承值：GCC UFS 页、PCIe phy-sequence——确认为 taro 硅片常量（与 board 无关），本机 live FDT 节点（ufshc/pcie）实测存在，2026-11-18 关闭。
- [ ] 面板 DCS/DSC 逐项核对（LTPO 1440×3200，pong/mondrian 面板不同）。
- [ ] 音频功放/路由：本机是 WCD938x 族 + `waipio-mtp-snd-card`，不能直接抄 pong 的 TFA9873。
- [ ] `proprietary-files.txt`：补齐 unicorn 自己的固件清单（GPU/Wi-Fi/触摸固件从本机提取）。

## 数据安全第一优先级

- [ ] userdata 尾部 64 GiB 窗口安装前，先收缩安卓 data 并复核 GPT。
- [ ] 全程只用 `fastboot boot`；禁止 `fastboot flash persist` / `flash all`。

## 命名归一化（不影响构建，可延后）

- [ ] `scripts/*.py` 里的 `pong_*` boot-arg/探针/路径逐步改为 `unicorn_*`（改一处要同步所有引用，避免打断已验证的 M1–M3）。
- [ ] `kits/PongPlatform24` 与 `MACHINE_CONFIGS=PONG` 保持不动：这是构建开关，不是设备名，改名会破坏 darwin24 聚合内核。
