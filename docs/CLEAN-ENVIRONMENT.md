# 干净环境验收方法

本项目首个完整包目标为 Debian 13、GNOME 48、Wayland、x86_64。
验收区分从干净文件系统构建、独立 GNOME 图形会话和实际物理桌面；三者不能互相替代。

## 构建环境

2026-10-22 的验收使用官方 `debian:13-slim` amd64 OCI 文件系统，镜像摘要为
`sha256:4876fdea29cac1a33a3195f1eb1952feb1fca7dd6dd00be3e2f1879cf20d34d2`。
下载后核对 manifest 与 layer SHA-256，再在独立 rootfs 中安装
`packaging/debian13-build.lock.json` 指定版本的依赖。没有安装或升级宿主系统软件。

无系统级容器服务的机器可使用 PRoot 完成 rootfs 内的 APT 配置，再用 Bubblewrap 执行原生构建。
本次 PRoot 5.5.0 官方静态程序 SHA-256 为
`db185300a9daabbce86aca7632d8c7fdc4249f6f153171954013b70c5f491ec0`。
它只参与环境准备，不进入程序包，也不参与最终渲染。

rootfs 中的 `/work/project` 是独立 Git 克隆；不挂载宿主头文件、库、旧构建或 sysroot。
在其中建立 `deps/sysroot -> /`，按锁文件生成 `deps/packages.txt`，执行：

```bash
bash packaging/build-backend.sh
WALLPAPER_BUILD_DIR="$PWD/build/package-renderer" make check
python3 packaging/build-package.py --build-dir build/package-renderer --output dist/clean
```

构建脚本在 sysroot 指向系统 `/usr` 时使用编译器原生搜索路径，避免重复插入系统头文件路径破坏 `include_next`。
源码快照检查拒绝追踪生成目录、私人资源及绝对路径链接。

## 图形运行

在宿主项目内调用：

```bash
python3 packaging/check-clean-desktop.py /独立/rootfs \
  /work/project/dist/clean/gnome-wallpaper-v0.0.3-linux-x86_64.shell-extension.zip \
  --runtime /用户自备测试资源目录
```

增加 `--video` 可测试自建合成视频。资源目录包含 `assets/`、`wallpapers/`，仅用于私有验收，不进入发行包。
工具在 rootfs 内运行 GNOME、GJS、GTK、安装器及完整包；只读挂载测试资源和用于兼容验证的扩展代码。
实际图形阶段再次隐藏源码、构建、旧 runtime，安装后的程序目录只读。
独立 HOME、XDG、会话与系统 DBus 隔离设置、日志与进程；为无系统登录服务的测试用户提供 passwd 记录，并明确设置 Wayland 会话标识。检查前后比较宿主 GNOME 设置。

检查包括静态应用列表、管理界面、动态播放、独立高质量截图、工作区、全屏、焦点通知、空工作区和回收。
rootfs 与宿主共享内核和 GPU 设备，所用 Mesa 用户态库来自 rootfs；这不是独立虚拟机或另一种显卡的兼容认证。
具体通过情况记录在 [验证记录](PACKAGING-VALIDATION.md)。

## 对应源码

```bash
python3 packaging/fetch-sources.py dist/clean/backend-manifest.json build/dependency-sources
python3 packaging/verify_sources.py dist/clean/backend-manifest.json build/dependency-sources
WALLPAPER_DEPENDENCY_SOURCES="$PWD/build/dependency-sources" make release-package
```

源码验证不仅检查目录索引和文件哈希，还核对每份 `.dsc` 的 Source、Version、归档大小及 SHA-256。
所有实际打包的 Debian 私有库和编译输入必须有精确版本对应源码；不以接近版本替代。
最后一行仅生成本地产物，不上传、发布或创建标签。

## 当前会话升级

`packaging/check-session-update.py` 使用独立 GNOME 会话验证：旧模块仍缓存时原子安装完整包、显式加载新模块、重复调用、动态播放与静态回收。
`gnome/scripts/stage-package-session.py` 仅在用户 state 目录准备版本隔离的模块；安装目录保持完整性。
用户显式运行 `gnome/scripts/apply-full-package.js` 后才更新当前会话。
此入口是维护辅助工具，不是日常启动器；正常登录直接加载标准扩展目录中的完整包。
