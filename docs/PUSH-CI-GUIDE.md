# 推送与 CI 触发指南（由你操作，10 分钟）

设备仓已就绪：`D:\UniXNU\UniXNU-unicorn`，分支 `master`，单 commit `7a38aac`（588 文件 / 22.7 MiB）。
**只需要推这一个仓库**——固件 CI 会自动拉取 `zhouzhoublm/uefi-unicorn`。

## 1. 创建 GitHub 仓库

<https://github.com/new> → 名字建议 `UniXNU-unicorn` → Private 或 Public 都行 → 不要勾选任何初始化选项（README/license/gitignore 都不勾）。

## 2. 推送

```bash
cd /d/UniXNU/UniXNU-unicorn
git remote add origin https://github.com/<你的用户名>/UniXNU-unicorn.git
git push -u origin master
# 浏览器会弹出 GitHub 登录授权，按提示完成即可
```

## 3. 配置 secret（关键）

仓库页面 → **Settings → Secrets and variables → Actions → New repository secret**

- Name: `UNIXNU_UNIQUE_CHIP_ID`
- Secret: `ba5846c1`

（来源：fastboot `cpuid=0x0000043bba5846c1` 的低 32 位。CI 首跑时核对一次 ADT 输出。）

## 4. 触发两个 workflow（Actions 页 → 各自 Run workflow）

| workflow | 参数 | 产物 | 用时 |
| --- | --- | --- | --- |
| `firmware-unicorn` | target=RELEASE | `unicorn-fd-RELEASE`（SILICIUM_UEFI.fd） | ~30–60 分钟 |
| `kernel-macos` | 默认（os_profile=22H374，prelink=false，volume_layout_run 留空） | `unicorn-kernel-payload-boot` + `unicorn-userdata`（含 volume-layout） | ~60–90 分钟 |

两个可以同时跑（不同 job 类型，互不抢资源）。

## 5. 下载产物并放到本机

把三个产物下载解压后放到：

```
D:/UniXNU/artifacts/fd/SILICIUM_UEFI.fd
D:/UniXNU/artifacts/kernel/    （kernel.macho、payload.img 等）
D:/UniXNU/artifacts/userdata/  （userdata 镜像分卷 + ci-volume-layout.json）
```

然后告诉我，我本地跑 `make-m3-image.sh` 打包并陪你上机 `fastboot boot`。

## 首跑失败的预期

CI 首跑失败是正常现象（内核构建对 runner 环境敏感）。失败后把 Actions 的失败日志
（红叉那一步的最后 100 行）发我或让我从 `gh`/网页读，我来修 workflow/脚本。
