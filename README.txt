GNOME Wallpaper — v0
====================

GNOME Wayland 上的 Wallpaper Engine 场景/视频壁纸管理器。
使用独立的 portghost C++ 渲染器和 GNOME Shell 插件，支持静态优先、显式动态播放。
项目：https://github.com/zcmmy/gnome-wallpaper

功能
- 静态缩略图与大图预览，导入壁纸、移入回收站删除和切换壁纸。
- 选择壁纸后先应用其静态图；只有明确开启动态模式才启动渲染器。
- 动态开关跨壁纸延续；全局帧率上限默认 15 FPS。
- 支持动画、频谱与鼠标交互，具体兼容性取决于壁纸效果。
- 默认关闭轮换；开启后默认每 30 分钟切换，支持顺序或可恢复的伪随机序列。
- 支持用户提供 static-background.png；缺图时明确开启动态可触发一次性辅助截图。
- 场景截图按 4K 可见区域渲染、缩小为 1080p；视频使用原生解码帧。
- 静态/动态壁纸兼容桌面和应用列表背景；不改变顶栏、Dock 的尺寸或样式。

验证范围与限制
当前本地验证平台为 Debian 13、GNOME 48、Wayland、x86_64。
上游 metadata 声明 GNOME 45–50，并不代表本项目 v0 已在这些版本全部验证。
v0 运行包以 scene/video 为目标；不包含完整的 CEF Web 壁纸运行依赖。
静态模式不启动渲染器、音频采集或鼠标桥；轮换开启时保留必要的调度。
高质量截图会有短暂额外负载，任务结束即退出，不改变普通动态播放设置。
不提供自动登录启动脚本；手动启用 GNOME 扩展本身可能在后续登录恢复启用状态。

获取、构建、安装
  git clone git@github.com:zcmmy/gnome-wallpaper.git
  cd gnome-wallpaper
  git switch --detach v0       # 查看固定 v0；继续开发使用 main 或新分支
  make help

源码已包含修改后的两层实现和上游自带的 External 源码，无需递归初始化 submodule。
构建依赖、资源准备和首次安装步骤：docs/INSTALL.txt。
  make renderer               编译 C++，可能下载固定版本的 CEF 构建依赖
  make extension              仅生成插件 ZIP，不安装、不启用
  make check                  本地回归；C++ 视频测试需要已构建的渲染库
  make package DEST=/新目录   打包独立运行目录，目标必须不存在

仓库不包含 Wallpaper Engine assets、Workshop 壁纸、个人静态截图或预编译库。
这些资源必须由用户自行准备；缺少资源不影响阅读源码、打包插件和运行无素材的单元测试。
独立运行目录可移走源码后继续使用，但仍依赖操作系统的 GNOME、图形驱动及系统库。

目录
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

文档
  docs/INSTALL.txt         新机器依赖、资源、构建、部署与禁用
  docs/ARCHITECTURE.txt    进程职责与静态/动态/截图数据流
  docs/DEVELOPMENT.txt     开发和安全部署
  docs/VERSIONING.txt      Git 工作流、v0、上游更新和备份
  docs/RUNTIME.txt         独立运行包说明，也是打包文档模板
  docs/VERIFICATION.txt    单元测试与需要私人素材的集成测试
  docs/MAINTENANCE.txt     目录所有权与安全清理
  third_party/README.txt   上游项目、传递依赖和许可证边界
  CHANGELOG.txt            版本记录

来源
渲染层基于 portghost-dev/linux-wallpaperengine，后者源自 Almamu/linux-wallpaperengine。
GNOME 层基于 diaslucass/wallpaperEngineWayland。
URL、固定 commit、上游 tree 和许可证位置见 third_party/sources.lock.json。
当前实现以本仓库源码和顶层文档为准，上游保留的 README/docs 描述其原始项目。
