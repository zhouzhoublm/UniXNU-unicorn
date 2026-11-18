# unicorn 构建与上机 Runbook

> 这份 runbook 把"在哪个环境做什么、做完看什么"写清楚。请在**理解每一步的副作用**后执行。
> 本文件中所有命令都不会自动刷写分区；唯一的设备写操作是显式执行 `fastboot flash`，本流程**不使用它**。

## 0. 环境与红线

| 需求 | 用途 | 本地是否具备 |
| --- | --- | --- |
| Windows + Git Bash / WSL | 仓库管理、离线校验、ADB 采集 | ✅ |
| Python 3.11+ | TOML/JSON 校验、`unixnu` 命令 | ✅（本机 3.13） |
| adb / fastboot | 只读采集、`fastboot boot` | ❌ 需安装 Platform Tools |
| macOS 15 + Xcode（或 GitHub Actions `macos-15-intel`） | XNU 编译、APFS 卷、payload | ❌ 本环境不具备 |
| `uefi-unicorn` 固件仓 + EDK2/Mu 子模块 | 生成 `SILICIUM_UEFI.fd` | ✅ 源码已拉取到 `D:/UniXNU/uefi-unicorn`；编译需 macOS/Linux |
| 合法获取的 iPadOS 18.7.10 / 22H374 IPSW | OS/SystemOS/Data 卷 | ✅ URL 可达（7,891,396,130 字节），但本环境无法解包 |
| 解锁 BL 的小米 12S Pro | 真机验证 | ❌ 需用户连接 |

**数据安全红线（不可协商）：**

1. Bring-up 阶段只用 `fastboot boot`，镜像只进 RAM，重启即回到原系统。
2. 禁止 `fastboot flash persist`、`fastboot flash all`：TEE 密钥永久损坏且不可恢复。
3. UniXNU 的窗口在 userdata 尾部 64 GiB；**安装前必须收缩 Android data 文件系统并复核 GPT**。
4. 任何需要写设备的操作，先做完整备份并明确确认目标分区。

## 1. 只读取证（在手机上）

手机开启 USB 调试并 root（采集脚本只读）：

```bash
# Windows Git Bash，仓库根目录
bash scripts/collect-device.sh --output ../evidence/unicorn-$(date +%Y%m%d)
```

采集内容：live FDT、`/proc/iomem`、分区几何、输入设备、显示、无线、电源、`getprop`、`/proc/cmdline`。
脚本在主机生成 `MANIFEST.tsv`（路径/大小/sha256），**不在手机上写任何文件**。

交叉检查：

```bash
python3 scripts/audit-inherited-values.py
python3 scripts/validate-offline.py --md docs/OFFLINE-VALIDATION.md
```

`validate-offline.py` 的 ERROR 必须在构建前清零；WARN 逐条记录到 `docs/BINDING-PLAN.md`。

## 2. 准备构建树

本工作仓按 format 2 依赖四层源码。目录布局：

```
D:/UniXNU/
├── UniXNU-unicorn/     # 本仓（设备层）
├── UniXNU/             # 官方框架，pin 见 docs/FEASIBILITY.md
├── soc-seed/           # 由 migrate-pong-format2.py 确定性生成的 SM8475 种子
├── uefi-unicorn/       # 固件层（独立仓）
└── build/              # 构建产物
```

在当前网络环境里 `git clone github.com` 的 CONNECT 隧道会 502；可改用 GitHub 官方 tarball。**这一步已在本机执行完成**，结果如下（重建时按同样步骤）：

```
D:/UniXNU/
├── UniXNU-unicorn/     # 本仓（设备层）
├── framework-pin/      # UniXNU @ 0fc0fc1（固定 pin）
├── soc-seed/           # 确定性 SM8475 种子，HEAD a107f6a
├── uefi-unicorn/       # 固件层 @ 2a128a83，子模块已从上游补齐
├── refer/apple/        # Apple OSS tarball 缓存
├── tools/platform-tools/  # adb / fastboot
└── framework-pin/out/unicorn/ipados-18.7.10-22H374/unicorn_ipados18/tree
```

已核验：`unixnu status` 解析成功（EXIT=0），soc-seed SHA 与 `migration-state.json` 一致，`tree` 已组装。Windows 下 `unixnu tree` 会因 tarball 无 `.git` 而在 `git submodule update` 处失败，等价的纯文件组装已完成（子模块源码已按 pin 放到 `framework-pin/drivers`、`framework-pin/kits`）。

**固件仓的坑**：`zhouzhoublm/uefi-unicorn` 的 6 个子模块在 git 树里是指向作者本机 `/root/uefi-unicorn/...` 的符号链接（mode 120000），在任何其他机器上都是断链。本机已用上游 tarball 替换：`microsoft/mu_basecore@release/202608`、`microsoft/mu_plus@release/202608`、`microsoft/mu_oem_sample@release/202608`、`Project-Silicium/Silicium-ACPI@main`、`Project-Silicium/Device-Binaries@main`、openssl `67b5686b`。这些分支**不是**上游 pin——固件编译前应按 `PORTING-TODO.md` 核对与 M1/M2 已验证版本的一致性。

引导命令（重建时）：

```bash
python3 scripts/migrate-pong-format2.py --unixnu ../framework-pin --soc ../soc-seed
cd ../framework-pin && python3 ./unixnu defconfig unicorn_ipados18_defconfig -D ../UniXNU-unicorn
python3 ./unixnu status -D ../UniXNU-unicorn
```

`migrate-pong-format2.py` 会安装 22H374 profile、写 `local.toml`、并校验 SoC 种子 SHA。

## 3. 编译 XNU 与 payload（macOS / GitHub Actions）

**本地 macOS**：在 Xcode 环境里执行官方链路，设备配置由 `board.toml` 解析：

```bash
./unixnu build kernel -D ../UniXNU-unicorn
./unixnu build payload -D ../UniXNU-unicorn
```

设备仓的 Darwin24 聚合内核入口是 `scripts/build-ipados18-pong-macos.py`，需要：

- `--volume-layout`：由 IPSW 生成的 APFS 卷布局，三个卷 UUID 会编进内核常量；
- `--developer-dir`：Xcode 路径；
- `refer/ipados18/` 下所有 source pin 到位（`unixnu fetch`）。

**没有 Mac 时**：用仓库自带的 `.github/workflows/package.yml`，在 Actions 页手动 Run workflow：

1. 选分支；OS profile 固定 `ipados-18.7.10-22H374`；
2. 填写合法获取的 `ipsw_url`（留空只能用 uuid5 占位 UUID，产物只能编译验证，不能上机）；
3. 配置仓库 secret `UNIXNU_UNIQUE_CHIP_ID`（本机平台种子，不进公开源码）；
4. 下载 `pong-package` / 对应 userdata 产物，校验 manifest。

**已知阻塞**：`docs/FEASIBILITY.md` 记录的"macOS 前置 `volume-layout.json` 绕不过"不是代码 bug，而是输入缺失；先解决 IPSW 与卷布局，再谈内核编译。`kits/PongPlatform24/build-support/merged-scripts/build-xnu-ipados18.sh` 是新 SoC 驱动链的合并脚本，但同样依赖 macOS SDK，不能在 Windows 上跑。

## 4. 组装可刷镜像

M1/M2 已验证的容器是 **Android boot header v4 + header_size 1584**，DTB 追加在 kernel 段，ramdisk 必须是 payload（不是空占位）：

```bash
bash scripts/make-m3-image.sh --payload <payload.img> \
    --target RELEASE --out ../out/m3-darwin24
```

脚本自校验：v4 头、DTB 魔数 `d00dfeed`、ramdisk 内含 `EFI/UniXNU/Payloads/*`。
`unixnu bootimg` 只支持 v0–v2，不能直接用于本机 ABL。

## 5. 上机（只进 RAM）

```bash
adb devices                       # 确认设备在线
adb reboot bootloader
fastboot devices
fastboot boot ../out/m3-darwin24/unicorn-uefi-M3-*.img
```

同时抓两份证据：

**USB 状态**（PowerShell，判断固件是否还在跑，不要靠 `adb devices`）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\boot-observe.ps1 -Seconds 180 -Interval 5 -OutFile evidence\boot-usb.csv
```

判读：UEFI 阶段没有任何 USB 设备；出现 `VID_18D1&PID_4EE7` 表示已回 Android；出现 `VID_1209&PID_0001` 是 XNU CDC 控制台。

**屏幕 / 日志**：屏摄菜单与 panic 文本；XNU 起来后用 ramoops / Advanced Logger QR 导出补日志。禁止靠"看起来没变"下结论。

只有 `fastboot boot` 返回后手机能正常回 Android，才算一次安全的 bring-up 循环。若手机卡在 UEFI/菜单，长按电源 10 秒强制重启。

## 6. 分阶段验收

| 阶段 | 看什么 | 通过判据 | 当前 |
| --- | --- | --- | --- |
| M1/M2 | UniXNU 菜单、音量/电源键 | 真机截图/录像 + USB 状态 | ✅ |
| M3 | 4 个启动项 | 清单与 ramdisk 一致；换 darwin24 内核后不再回落 shutdown | ◐ |
| M4 | XNU 启动检查点 | 可读 panic 或串口；launchd 启动 | ⛔ |
| M5 | UFS 三窗口 | GPT 与容量正确、Data 挂载 `/private/var` | ⛔ |
| M6 | 首帧 / 按键 / 触摸 | 已知画面 + 三条按键 HID + 单点触摸 | ⛔ |
| M7 | GPU / Wi-Fi / 音频 / 电源 | 每项独立八步证据 | ⛔ |
| M8 | 发布 | format 2 完整性 + 双语文档 | ⛔ |

## 7. 失败时的记录格式

每个候选镜像至少记四项：镜像路径与 sha256、构建输入 pin、最后一次成功的检查点、可复现的日志片段。
写 `porting.toml` 时区分：`source`（源码分析）、`host`（本机构建/静态校验）、`device`（真机观察）。**三者不能互相替代。**

## 8. 本环境残留任务

| 任务 | 需要 | 状态 |
| --- | --- | --- |
| 生成 22H374 kernel.macho / payload.img | macOS 15 + Xcode + IPSW 解包 | 阻塞 |
| 构建 `uefi-unicorn` 最终 FD | macOS/Linux + stuart_build；源码与子模块已就位 | 阻塞（仅差编译环境） |
| 提取 GPU/Wi-Fi/触摸固件 | 用户手机 vendor 分区 | 阻塞 |
| `fastboot boot` 与硬件验收 | 用户手机 + Platform Tools（已装到 `tools/platform-tools/`） | 阻塞 |
| 离线校验与文档 | 无 | ✅ 已完成 |
| 构建树 / SoC 种子 / 参考源码 / 工具链 / 固件源码 | 无 | ✅ 已完成 |
