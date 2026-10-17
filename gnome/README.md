# GNOME 适配层

extension/ 是修改后的 GNOME 插件源码，由顶层 Git 管理。只负责进程管理、窗口归属/层级、概览副本、指针桥和设置界面。
插件只认识一个可执行文件路径和 IPC 契约，不知道 C++ 的源码/构建目录。wallpaperengine-path 由部署层配置。

打包：scripts/build.sh，输出 build/gnome/wallpaperengine@waylandwe.zip。
插件仓库也能独立打包：extension/scripts/package.sh OUTPUT.zip。
测试：tests/check.sh。均不调用 CMake/C++、不下载渲染器、也不加载或启用扩展。
原 install-fedora.sh 的混合安装入口已退役；原文保存在 Git 历史。

scripts/live-desktop.js 与 apply-overview-fix.js 只是本地试运行工具，不进入插件发布包。
它们通过项目位置定位 runtime/live-extension，不能代替正式的插件安装/版本兼容管理。
运行时副本和当前会话的旧代码缓存保持原样；源码改动不会自动热更新当前 Shell。
跨层协议见 [../integration/contracts/renderer-control-v1.md](../integration/contracts/renderer-control-v1.md)。

## 管理界面与职责

```text
extension.js          GNOME 标准入口，导出 wallpaperExtension.js
wallpaperExtension.js WaylandClient 进程/窗口、背景层、指针桥、概览生命周期
manager.js            静态/动态状态切换、定时轮换、辅助截图文件监听和状态发布
library.js            库扫描、路径校验、用户图片导入与缩略图
rotation.js           纯序列生成，无 Shell/渲染器依赖
rendererClient.js     有超时的短连接 JSON IPC，串行更新全局 FPS
staticWallpaper.js    GNOME 原生壁纸与首次配置备份/显式恢复
managerUi.js          GTK4/libadwaita 页面，不参与后台调度
prefs.js              GNOME 扩展首选项入口
managerApp.js         独立管理窗口入口，UI 和首选项共用同一实现
```

GSettings 保存 library-root、selected-id、enabled、fps、轮换参数与序列。
runtime-status 仅为显示状态，DBus Snapshot 用于确认当前扩展实例是否存活。
GUI 通过设置变化发出命令，不持有渲染器；关闭 GUI 不影响播放/轮换。
静态模式不创建 OverviewWallpaper、不启动 PointerBridge、不启动后端。
已有图片不自动覆盖；缺图后明确启动动态才运行独立高质量截图任务，成功/停止/超时均清理。
动态加载失败保留静态背景，提示重试，不循环崩溃重启。
快速切换先停止旧进程，再启动最后一次选择；同时最多一个日常播放后端；一次性高质量截图使用单独进程。
全局 FPS 使用 set-fps IPC 生效，无需重启，快速输入会串行合并到最终值。

安装时使用打包/安装脚本，包含全部 *.js、captureWorker.py、libraryWorker.py、metadata.json 和 schemas。
源码与运行包不共享壁纸修改；用户应编辑已部署运行包的 wallpapers/<ID>/static-background.png。

## 安全更新

用 python3 scripts/install-extension.py SOURCE DESTINATION 安装；或运行包的 bin/install-gnome。
先在临时目录编译 schema，再原子交换整个扩展目录。旧实例继续读取旧 inode，新实例读取新 schema。
禁止对运行中扩展使用 cp/copytree 覆盖 gschemas.compiled；该文件被 GSettings 内存映射，破坏后可能令整个 Shell 致命退出。
安装器不修改 GSettings、不启用插件。原子映射保护与无效更新保留原文件由 tests/check-schema-update.py 验证。

高质量静态截图（2026-10-17）：captureWorker.py 是仅任务期间运行的 Python/GdkPixbuf 辅助程序，使用私有 D-Bus、XDG 目录和无界面的 GNOME Wayland 合成器运行一次性渲染器，不连接实际桌面。依赖系统已有 python3-gi、GdkPixbuf、gnome-shell、dbus-run-session 和 gdbus。默认场景 4K 渲染后保存 1080p；视频从原生帧缩小。任务按用户串行执行，正常完成、超时、切换壁纸、关闭动态或禁用扩展均清理子进程；用户自行提供的静态图优先，禁止覆盖。
缺少静态图时仍遵循显式授权规则：静态模式只提示，用户开启动态后才后台生成高质量静态图。普通播放进程不传 screenshot 参数。截图会产生短暂额外负载，结束后无常驻截图服务。失败保留原生背景，可重新开启动态重试。
独立调用：python3 /路径/gnome/wallpaperengine@waylandwe/captureWorker.py --renderer /路径/bin/renderer --assets /路径/assets --scene /路径/wallpapers/ID --output /路径/output.png
--diagnostics DIR 保存过程日志和实际 FBO 尺寸；--quality standard --freeze 仅用于固定动画状态的对照测试。

静态概览背景：staticOverview.js 仅在概览/应用列表可见且动态画面未就绪时，创建 GNOME BackgroundManager 原生背景层，复用当前原生壁纸与缓存。退出概览后销毁 actor 和对应背景管理器；不启动渲染器、截图任务、鼠标桥或轮询计时器。动态画面就绪时由原有动态概览层接管，禁用扩展时释放信号。integration/tests/check-static-overview.py 在隔离 GNOME 中结合当前 Blur my Shell、Dash to Dock 配置验证切换和清理，并生成应用列表截图。
