# unicorn 板级绑定方案（从 pong/thor/mondrian 迁移到本机）

本文件回答一个具体问题：**同 SoC 的现成代码里，哪些可以直接用，哪些必须换成 unicorn 的本机值，换成什么，怎么验证。**

## 一、复用分层

```
ARM64 公共层        UniXNU/profiles/arch/arm64               直接复用
SM8475 SoC 层       UniXNU-sm8475-common（dtsi/config/补丁）  直接复用，pin 固定
22H374 OS 层        os-profiles/ + XNU 11417.140.69           直接复用，prelink 规则不变
板级层              board.toml / dts/unicorn.dts / defconfig   本机实测，逐项替换
驱动层              kits/PongPlatform24 + drivers/*           同 SoC 可用，板级输入必须替换
固件层              uefi-unicorn（由 uefi-mondrian 派生）      已能出菜单，内存表仍需收敛
```

**铁则：任何板级数值必须能在 `verified-facts.json` 或 `docs/HARDWARE-FACTS.md` 找到出处。** 没有出处的值在 DTS 里标 `TODO(verify)`，在对应驱动启用前必须关闭。

## 二、逐项绑定矩阵

| # | 子系统 | 基线来源 | unicorn 本机值 | 需要改的文件 / 代码 | 验证判据 |
| --- | --- | --- | --- | --- | --- |
| 1 | SoC / CPU | pong / thor | SM8475，X2+3×A710+4×A510，PSCI/GICv3 | 继承；`configs/unicorn_ipados18_defconfig` 保持 `CONFIG_XNU_ARMCPU=y` | 八核寄存器进入各自的 entry checkpoint；单核 `cpus=1` 先过 |
| 2 | DRAM / 保留区 | 本机 live DT | 12 GiB @ `0x80000000`，38 段 reserved-memory，ramoops `0xa7000000+0x400000` | `dts/unicorn.dts`；UEFI `MemoryMapLib` 目前沿用 K60 表 | 菜单能稳定 90 s；内核内存图与 `/proc/iomem` 对齐 |
| 3 | UEFI FD / 栈 | 本机 iomem | FD `0xA7400000` 长 `0x300000`；栈 `0xA7700000` | `uefi-unicorn` 平台配置；`verified-facts.json` | 脚本校验落点不在任何保留区内；真机出菜单 |
| 4 | 显示 | pong 1080×2412 | `qcom,mdss_dsi_l2s_38_0c_0a_dsc_cmd`，1440×3200，DSC 10bpc，LTPO | 面板 DCS 序列（`docs/PANEL-L2S-DCS.txt`）、stride、刷新率、背光 | 已知画面首帧；panic 文本可读；亮度可控 |
| 5 | 触摸 | pong Goodix / K60 Goodix BRL | **FocalTech FTS**：SPI `0x990000`，IRQ GPIO 21，RST GPIO 20，12 MHz，原始轴 14400×32000 | 新 FTS 驱动或 `unicorn-touch` 节点；DTS 当前 `status="disabled"` | CFG 握手 ACK、坐标上报、HID 派发、单点→多点 |
| 6 | 按键 | pong PON `0x18d` | 电源 PON PPID `0x13`；音量上 TLMM GPIO 6 | `unicorn-buttons` 节点；XNU 侧 HID 映射 | UEFI 已验证；XNU 下 power/volup/voldown 三条报告 |
| 7 | UFS | 同 SoC | `1d84000.ufshc`，SPI 265，SID `0xe0`，2 lane，reset GPIO 210 | `&ufs` 节点；NativeUfs 驱动 | 容量/GPT 正确；OS/SystemOS/Data 挂载 |
| 8 | userdata 窗口 | 本机分区表 | 4K LBA `3013120…61731834`；尾部 64 GiB `0x2ADF3FB…0x3ADF3FA` | `board.toml [userdata]`；安装脚本 | 安装前收缩安卓 data；写入后重启安卓仍完好 |
| 9 | Wi-Fi / BT | pong QCA6490 | QCA6490，PCIe RC0 `0x1c00000`，GPIO 80/94/96/95/204 | `&pcie0` 节点；固件 `qca6490/*` 从本机提取 | PCIe 枚举、MHI mission mode、扫描关联 |
| 10 | GPU | pong Adreno 730 | Adreno 730 v3，芯片 `0x07030002` 族 | 固件从 vendor 提取；defconfig 后期打开 `CONFIG_XNU_PONG_ADRENO_PLATFORM=y` | GMU/CP 启动 22 步 result=0；Metal 设备发布 |
| 11 | 音频 | pong TFA9873 双功放 | WCD938x 族 / `waipio-mtp-snd-card` | 需重新确认功放型号与路由；不可直接抄 TFA9873 | 播放提示音、音量、休眠恢复 |
| 12 | USB | 同 SoC | `a600000.dwc3` + eUSB2 repeater + `fsa4480` | 基本沿用；mux 与 DMA 参数核对 | CDC 控制台回环 |
| 13 | 电池 / 充电 | 需重测 | 4600 mAh，120 W 有线 / 50 W 无线 | 采集 power supply 曲线后再接 | 电量、温度、充放电状态正确 |

## 三、当前已发现的具体偏差

1. **触摸原始轴。** `verified-facts.json` 与 live DT 记录 `x-max=14400 / y-max=32000`，但 `dts/unicorn.dts` 的 `unicorn-touch` 节点写的是 `max-x = <1440> / max-y = <3200>`（面板像素）。这**不一定是错**：UI 用像素，驱动用原始轴。但 FTS 驱动实现时必须明确使用 `14400×32000`，否则会出现"只有左上角能点"的典型症状。K60 的 Goodix 线也踩过同一个坑（模块名不能推断协议、evdev 原始轴不能被像素覆盖）。
2. **保留区数量（已修正）。** `docs/HARDWARE-FACTS.md` 写 38 段，基线 DTS 注释误写 36 段；离线校验器实测 DTS 确有 38 个 `reserved-memory` 条目，注释已改正。内存描述符本身仍需按 M3 后内核日志收敛。
3. **继承值。** `dts/unicorn.dts` 里 `pong,gcc-ufs-page` 和 PCIe phy-sequence 仍标 `TODO(verify)`，属同 SoC 继承，需要 vendor 内核或 live DT 交叉验证。
4. **userdata 窗口是 provisional，且原仓库的十六进制字面量写错了。** `first_lba = 0x2ADF3FB` / `last_lba = 0x3ADF3FA` 才是实测的 44954619 / 61731834；基线仓库的 `0x2AE13BB` / `0x3AE1F7A` 与注释里的十进制对不上（相差 3008 个 4K 块）。本工作仓已改正，并在 `scripts/validate-offline.py` 里加了回归检查。**在收缩 Android data 并复核 GPT 之前仍不得写入。**
5. **README_EN.md 曾整篇是 pong 文档**，已在本工作仓替换；引用它的旧外部记录不可信。

## 四、驱动适配顺序（依赖优先，不要跳步）

1. **platform / memory**：ADT `/chosen`、`/cpus`、`/arm-io`；保留区与 DMA 窗口。
2. **storage**：NativeUfs → GPT → APFS 三窗口 → launchd。没有根设备，后面什么都看不到。
3. **display / backlight**：先复用 UEFI 已验证的 GOP 通路；内核侧先出首帧与 panic 文本。
4. **input**：实体键（已有实测数值）→ FTS 触摸（新驱动，八步流程）。
5. **GPU / Metal**：固件与 CP 启动，最后接 scanout。
6. **Wi-Fi / BT**：PCIe + MHI + 固件；注意 SMMU 锁的初始化顺序（K60 P-215 的教训）。
7. **audio / power**：ADSP PAS1、codec、电池/充电曲线。
8. **cellular / DSP**：明确记录为 planned，不要为了"看起来完整"伪造状态。

## 五、每一步的证据要求

沿用 mondrian 的八步：**① 同型 → ② 官方 → ③ 反编译 → ④ 广域 → ⑤ 方案 → ⑥ 深挖 → ⑦ 核验 → ⑧ 上机**。

- ①②④ 是只读研究：同 SoC 实现、厂商/官方驱动、反汇编、其他设备案例；
- ⑤⑥ 是设计；⑦ 是主机侧可复现的构建/静态/容器校验；⑧ 才是真机。
- 只有 ①–⑦ 全通才允许生成 `fastboot boot` 候选镜像；任何一步缺失都要在 `porting.toml` 里留 `planned`，不能写成 `implemented`。
- 上机一律 `fastboot boot`（RAM 临时引导），**不 flash 任何分区**；禁止 `fastboot flash persist` 与 `flash all`。

## 六、需要用户补充的输入

| 输入 | 为什么需要 | 获取方式 |
| --- | --- | --- |
| 合法获取的 22H374 IPSW URL | 生成 OS/SystemOS 卷与卷 UUID | Apple 官方 restore 链接，写进 `board.toml [ipsw].url` |
| `UNIXNU_UNIQUE_CHIP_ID` | ADT 平台身份与 BT MAC，按芯片唯一 | GitHub Actions secret；不能写死在公开仓库 |
| 本机 vendor 分区固件 | GPU/Wi-Fi/触摸固件二进制 | 从自己手机的 vendor 分区只读提取 |
| 收缩后的 userdata 布局 | 避免破坏安卓数据 | 在手机上完成文件系统收缩后再采集 GPT |
| 真机 USB 访问 | `fastboot boot`、串口/日志 | 解锁 BL 的手机 + USB 线 |
