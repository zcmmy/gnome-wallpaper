# GNOME Wallpaper — v0

GNOME Wayland 上的 Wallpaper Engine 场景/视频壁纸管理器。
使用独立的 portghost C++ 渲染器和 GNOME Shell 插件，支持静态优先、显式动态播放。
项目：[zcmmy/gnome-wallpaper](https://github.com/zcmmy/gnome-wallpaper)

## 功能

- 静态缩略图与大图预览，导入壁纸、移入回收站删除和切换壁纸。
- 选择壁纸后先应用其静态图；只有明确开启动态模式才启动渲染器。
- 动态开关跨壁纸延续；全局帧率上限默认 15 FPS。
- 支持动画、频谱与鼠标交互，具体兼容性取决于壁纸效果。
- 默认关闭轮换；开启后默认每 30 分钟切换，支持顺序或可恢复的伪随机序列。
- 支持用户提供 static-background.png；缺图时明确开启动态可触发一次性辅助截图。
- 场景截图按 4K 可见区域渲染、缩小为 1080p；视频使用原生解码帧。
- 静态/动态壁纸兼容桌面和应用列表背景；不改变顶栏、Dock 的尺寸或样式。

## 验证范围与限制

当前本地验证平台为 Debian 13、GNOME 48、Wayland、x86_64。
上游 metadata 声明 GNOME 45–50，并不代表本项目 v0 已在这些版本全部验证。
v0 运行包以 scene/video 为目标；不包含完整的 CEF Web 壁纸运行依赖。
静态模式不启动渲染器、音频采集或鼠标桥；轮换开启时保留必要的调度。
高质量截图会有短暂额外负载，任务结束即退出，不改变普通动态播放设置。
不提供自动登录启动脚本；手动启用 GNOME 扩展本身可能在后续登录恢复启用状态。

## 获取、构建、安装

```bash
git clone git@github.com:zcmmy/gnome-wallpaper.git
cd gnome-wallpaper
make help
```

源码已包含修改后的两层实现和上游自带的 External 源码，无需递归初始化 submodule。
构建依赖、资源准备和首次安装步骤：[docs/INSTALL.md](docs/INSTALL.md)。

```text
make renderer               编译 C++，可能下载固定版本的 CEF 构建依赖
make extension              仅生成插件 ZIP，不安装、不启用
make check                  本地回归；C++ 视频测试需要已构建的渲染库
make package DEST=/新目录   打包独立运行目录，目标必须不存在
```

仓库不包含 Wallpaper Engine assets、Workshop 壁纸、个人静态截图或预编译库。
这些资源必须由用户自行准备；缺少资源不影响阅读源码、打包插件和运行无素材的单元测试。
独立运行目录可移走源码后继续使用，但仍依赖操作系统的 GNOME、图形驱动及系统库。

## 目录

```text
renderer/source/         修改后的 portghost 渲染源码（完整纳入顶层 Git）
renderer/scripts/       渲染层构建、运行入口；renderer/tests/ 为独立测试
gnome/extension/         修改后的 GNOME 扩展、管理 UI 与一次性任务
gnome/scripts/          插件打包、原子安装及会话工具；gnome/tests/ 为独立测试
integration/            两层协议、打包、维护、图形集成测试
third_party/            固定上游来源、基线改动索引和许可证引用
docs/                   安装、架构、开发、运行、验证、版本管理文档
sources/、tools/         旧命令及 CMake 缓存的兼容入口
assets/、wallpapers/、wallpaper/、deps/、build/  本地资源与生成物，Git 忽略
runtime/、reports/、backups/、logs/           本地状态/报告/备份，仅说明文件入库
```

## 文档

- [安装与依赖](docs/INSTALL.md)
- [架构与数据流](docs/ARCHITECTURE.md)
- [开发和安全部署](docs/DEVELOPMENT.md)
- [Git 版本管理](docs/VERSIONING.md)
- [独立运行包](docs/RUNTIME.md)
- [测试与验证](docs/VERIFICATION.md)
- [目录维护与备份](docs/MAINTENANCE.md)
- [上游项目与依赖](third_party/README.md)
- [更新记录](CHANGELOG.md)

`main` 包含最新文档；`v0` 标签保留首次发布的历史快照。

## 开源许可与来源

本项目原创代码和修改采用 **GPL-3.0-only**，继承 portghost 的 GPLv3 开源方式。
完整条款见 [LICENSE](LICENSE)，第三方归属与许可例外见 [NOTICE.md](NOTICE.md)。

核心渲染器基于 [portghost-dev/linux-wallpaperengine](https://github.com/portghost-dev/linux-wallpaperengine)，
固定基线为 [`50530e5167c0822e63f052f50ef8d8613663915a`](https://github.com/portghost-dev/linux-wallpaperengine/tree/50530e5167c0822e63f052f50ef8d8613663915a)。
感谢 portghost、[Almamu](https://github.com/Almamu/linux-wallpaperengine) 及其贡献者提供的引擎基础。
上游能力、本项目改动、GNOME 扩展来源及传递依赖详见 [第三方引用](third_party/README.md)。

GNOME 层基于 [diaslucass/wallpaperEngineWayland](https://github.com/diaslucass/wallpaperEngineWayland)。
机器可读的固定来源见 [sources.lock.json](third_party/sources.lock.json)。
当前集成以本仓库顶层文档为准，保留的上游 README/docs 用于描述原始项目。
