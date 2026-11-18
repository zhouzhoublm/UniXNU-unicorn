# 小米 12S Pro（unicorn）移植 UniXNU 可行性评估

日期：2026-11-18
对象设备：Xiaomi 12S Pro，型号 **2206122SC**，代号 **unicorn**，SoC **SM8475 / taro**，Adreno 730 v3。
参考路线：Redmi K60（mondrian）+ 上游 UniXNU + Nothing Phone (2)（pong）/ 小米 12S Ultra（thor）/ 现有 unicorn 仓库。

## 一、结论

**可行，且不是从零开始。** 可行性的三个决定性依据：

1. **SoC 完全相同。** mondrian、pong、thor、unicorn 都是 SM8475。CPU/GIC/timer、UFS 控制器族、Adreno 730、QCA6490 的 SoC 层资源与补丁可以复用；上游 UniXNU 的设备仓库本来就按 ARM64 → SoC → OS → 设备四层拆分，这正是为这种同 SoC 换板场景设计的。
2. **目标系统有成熟先例。** pong 和 thor 已经把 **iPadOS 18.7.10 / 22H374 / darwin24** 跑到桌面，触控、Wi-Fi、音频、GPU/Metal 都有真机记录；unicorn 直接采用同一 OS profile，不需要重做 XNU/prelink ABI。
3. **这块板子的前期工作已经做完。** `zhouzhoublm/UniXNU-unicorn` 已有 13/13 项本机实测硬件事实，UEFI 菜单、实体键、payload 清单渲染都已在真机上出现（M1–M3）；缺的是 darwin24 内核产物与后续硬件栈。

**但必须说清楚边界：** 这不是"装一个包就能用 iOS"。当前仓库的阻塞点是内核构建需要 macOS/Xcode 与 `volume-layout.json`，UEFI 固件仓与私有固件需要从手机提取，所有 XNU 阶段结论必须真机 `fastboot boot` 验证。这些步骤无法在本次离线环境中完成。

**离线校验中发现并已修正的两个基线缺陷**（详见 `docs/OFFLINE-VALIDATION.md`）：

- `board.toml` 的 userdata LBA 十六进制字面量与注释里的十进制不一致：`0x2AE13BB` / `0x3AE1F7A` 实际是 44,962,747 / 61,742,970，而实测应为 44,954,619 / 61,731,834，即 `0x2ADF3FB` / `0x3ADF3FA`。若按错误值装机，窗口会偏移 3,008 个 4K 块（约 11.7 MiB）。已修正并加入回归检查。
- `dts/unicorn.dts` 注释写 36 段保留区，实际有 38 段；注释已改正。

## 二、三条参考路线的可复用范围

| 参考 | 系统 / 内核 | 已有成果 | 对 unicorn 的可复用部分 | 不可直接复用部分 |
| --- | --- | --- | --- | --- |
| `Emilelu/UniXNU-mondrian`（Redmi K60） | iOS 16.6.1 / darwin22 | 触摸、存储、显示、启动链、USB 八步全通；GPU ⑦ 已核验、音频卡在 ⑦ | 八步流程与证据格式、UFS 三窗口、启动镜像 v4 布局、坑记录 P-01–P230 | darwin22 ABI、Goodix BERLIN 触摸、K60 面板与电池栈 |
| `SFZ97/UniXNU-thor` → `pong`（12S Ultra / Phone 2） | iPadOS 18.7.10 / darwin24 | 桌面、触控、Wi-Fi、音频、GPU/Metal、按键有真机记录 | 整套 darwin24 驱动栈、defconfig、profile、脚本、ADT 生成 | 面板 DCS/DSC、触摸控制器、按键 PPID、userdata 几何 |
| `zhouzhoublm/UniXNU-unicorn` | 目标同上 | 硬件事实 13/13、M1/M2 菜单与按键、M3 payload 菜单 4 项 | 设备仓本身，就是本工作仓的基线 | 内核产物、UEFI 最终构建、XNU 阶段全部功能 |

**关键判断：** 选 **darwin24 / iPadOS 18.7.10** 路线，不要退回 mondrian 的 darwin22。原因是 unicorn 的 M3 已经证明固件与 payload 菜单可用，失败点正是"payload 里放的是 darwin22 内核，darwin24 DarwinBoot 的 boot_args ABI 是 0x480/1024，装载器拒绝后回落到 shutdown"。补一份 22H374 的内核即可跨过 M3。

## 三、板级差异清单（必须替换，不能继承）

| 子系统 | pong / mondrian 的值 | unicorn 实测值 | 影响 |
| --- | --- | --- | --- |
| 面板 | pong 1080×2412；K60 1440×3200 m11a | `l2s_38_0c_0a`，1440×3200，DSC 10bpc，LTPO 1–120 Hz | DCS 初始化与时序必须按本机 live DT 逐项核对；最高风险 |
| 触摸 | pong Goodix Berlin-D；K60 Goodix GT9916R（BRL） | **FocalTech FTS**，`fts@0`/SPI `0x990000`，IRQ GPIO 21，RST GPIO 20 | 现成 Goodix 驱动不能用，需要 FTS 协议实现；DTS 目前 `status="disabled"` |
| 按键 | pong 音量走 PON PPID `0x18d` | 电源 PON PPID `0x13`，**音量上 = TLMM GPIO 6** | UEFI 已验证可用；XNU 侧必须按 unicorn 数值接 |
| userdata | pong 分区几何不同 | 4K LBA `3013120…61731834`，尾部 64 GiB 窗口 `0x2ADF3FB…0x3ADF3FA` | 安装窗口前必须先收缩安卓 data，否则破坏安卓数据 |
| 音频 | pong 双 TFA9873 | WCD938x 族 / `waipio-mtp-snd-card` | 功放与路由不同，音频放到后期 |
| 内存 | pong/K60 各有保留区表 | 12 GiB @ `0x80000000`，38 段 reserved-memory；UEFI FD `0xA7400000` | 当前 UEFI 用 K60 MemoryMapLib 点亮；自生成表曾黑屏，需二分 |
| Wi-Fi | QCA6490 同族 | QCA6490，PCIe RC0 `0x1c00000`，wlan-en 80 / perst 94 / wake 96 / clkreq 95 | 同族，GPIO/固件位置需替换 |

详细绑定方案见 `docs/BINDING-PLAN.md`。

## 四、风险分级

| 等级 | 风险 | 现状 / 缓解 |
| --- | --- | --- |
| 高 | 内核构建链：需要 Xcode、`volume-layout.json`、APFS 卷 UUID 与内核常量一致 | 用 GitHub Actions `macos-15-intel` runner 打包；无 IPSW 时用 uuid5 占位只能编译验证，不能上机 |
| 高 | 面板 DSC/LTPO 初始化 | 已导出完整 DCS 序列到 `docs/PANEL-L2S-DCS.txt`；逐条比对 live DT，先在 UEFI 阶段保持已验证的 GOP 通路 |
| 高 | FocalTech 触摸没有现成 XNU 驱动 | 先做按键；触摸按"同型→官方→反编译→广域→方案→深挖→核验→上机"八步走，可借鉴 K60 BRL 的调试方法但不能抄协议 |
| 高 | userdata 窗口写入会破坏安卓数据 | 只用 `fastboot boot`；安装前必须收缩 Android data；绝不 `flash persist` / `flash all` |
| 中 | darwin24 prelink / boot_args ABI | 沿用 22H374 profile 与 pong 的 prelink 规则；M3 失败已定位为内核版本契约，不是容器问题 |
| 中 | GPU/Metal 需要厂商私有固件 | 后期从本机 vendor 分区提取；首启阶段 defconfig 里关闭 |
| 中 | Wi-Fi/蓝牙需要 Linux ath11k 源码与固件 | 后期打开；首次启动不需要 |
| 低 | CPU、UFS、按键、启动链 | 同 SoC 且 unicorn 已有真机证据 |

## 五、阶段计划与退出条件

| 阶段 | 内容 | 退出条件 | 状态 |
| --- | --- | --- | --- |
| M0 | 硬件事实采集 | 13/13 板级数值有本机出处，`audit-inherited-values.py` 无未解释项 | ✅ 已完成 |
| M1 | UEFI 上屏 | 真机出现 UniXNU 菜单 | ✅ 已完成 |
| M2 | 菜单操作 | 音量键移动、电源键确认、USB 状态判定正确 | ✅ 已完成 |
| M3 | payload 装载 | 菜单出现 4 个清单项；换成 22H374 darwin24 内核后装载器接受 | ◐ 清单已验证，内核未就绪 |
| M4 | 内核首启 | 串口/屏幕看到 XNU 启动并检查点，进 launchd | ⛔ 未开始 |
| M5 | 存储与 root | UFS 三窗口挂载、OS/SystemOS/Data 可读 | ⛔ 未开始 |
| M6 | 显示/触摸/按键 | 首帧 + 实体键 + 单点触摸 | ⛔ 未开始 |
| M7 | GPU/Wi-Fi/音频/电源 | 按优先级逐项八步核验 | ⛔ 未开始 |
| M8 | 完成与发布 | format 2 完整性、双语文档、证据可复现 | ⛔ 未开始 |

## 六、本次实际执行范围

已在本工作仓执行：

- 建立 `UniXNU-unicorn` 工作仓，基于 `zhouzhoublm/UniXNU-unicorn`（pin `a99b5c1`）；
- 补齐仓库声称存在但缺失的 `scripts/collect-device.sh`、`scripts/boot-observe.ps1`；
- 新增离线校验器 `scripts/validate-offline.py` 并生成 `docs/OFFLINE-VALIDATION.md`；
- 修正 README/English README、PORTING-TODO 的过期状态；
- 写出可行性、板级绑定、构建与上机三份文档；
- **搭建完整本地构建树**：框架 pin `0fc0fc1`、SM8475 种子（SHA `a107f6a` 校验一致）、22H374 profile、5 个 Apple 参考源码、19 个内核子模块、`unixnu status` 解析成功、树已组装；
- **装好真机工具链**（adb 37.0.1 / fastboot），核验 IPSW URL 可达（7.89 GB）；
- **拉取固件仓** `zhouzhoublm/uefi-unicorn` @ `2a128a83`（含 unicornPkg），并把 6 个被写成作者本机绝对符号链接的子模块替换为上游源码。

无法在本环境执行（需要用户或外部资源）：

- 编译 XNU / prelink / 打包 payload（macOS + Xcode + Apple 开源依赖）；
- 构建最终 UEFI 固件（源码已就位，仍缺 macOS/Linux + stuart_build）；
- 解包 IPSW 生成 `volume-layout.json`（IPSW URL 已核验，但需 macOS 的 `aea`/`hdiutil`）；
- 提取私有固件（需用户手机 vendor 分区）；
- 真机 `fastboot boot`、日志抓取、触摸/显示/音频验收。

## 七、参考与 pin

| 仓库 | 用途 | pin |
| --- | --- | --- |
| `Emilelu/UniXNU-mondrian` | K60 八步流程、坑记录、v4 镜像布局 | `b6787b4cc6a3c6e9005f1fbbf3c0ca338ba90482` |
| `SFZ97/UniXNU-thor` | 同 SoC、同 OS 的模板来源 | `e9c7f81a38dbca2a1ceba89ad38895d74d8ba5a9` |
| `zhouzhoublm/UniXNU-unicorn` | 本工作仓基线 | `a99b5c1d2128894519948eeee9faa49a7bc58021` |
| `UniXNU/UniXNU` | 官方框架、组件目录、format 2 规范 | `429d337ca53c8f88759710c4daf35bd6ff502f5f` |
| `zhouzhoublm/uefi-unicorn` | unicorn UEFI 固件（`Platforms/Xiaomi/unicornPkg`） | `2a128a83c124a446514afee13e76385d0319cee1` |
| `Emilelu/UniXNU-sm8475-common` | 共享 SM8475 资源（参考） | `main` |
| `UniXNU/UniXNU` | 本地构建树实际使用的框架 pin（与设备仓迁移状态一致） | `0fc0fc1f9ddd0fbd4787738afef38667df5e0a95` |

> 参考文献的 SHA 只用于说明本次判断基于哪个版本；上游持续推进，实际构建前按 `docs/BUILD-RUNBOOK.md` 重新解析 pin。
