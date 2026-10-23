# v0.1.0 完整发行包重构

## 目标和结果

旧版插件需要另行部署 C++ runtime 并配置本机路径，安装包与源码、程序、素材之间的关系不清晰。
v0.1.0 将运行程序收敛到一个完整 GNOME 扩展包，用户只需安装、导入自备资源、选择静态或显式开启动态。
技术路线继续使用 portghost 独立 C++ 渲染器，没有将渲染算法迁入 GNOME 或改变日常播放质量。

| 层 | 所有权与内容 | 生命周期 |
| --- | --- | --- |
| Git 源码 | 渲染层、GNOME 层、协议、构建安装工具、上游来源 | 按版本提交；不含素材和二进制 |
| build/ | CMake 缓存、编译结果、构建身份与依赖源码集合 | 可重建；不能混用 checkout |
| dist/ | 完整包、清单、对应源码和校验和 | 可独立分发 |
| 扩展安装目录 | JS/Python、schema、后端、私有库和许可证 | 整体校验、原子替换、可回滚 |
| XDG data/cache/state | 素材、静态图、索引、缩略图、恢复记录和日志 | 与程序独立；更新保留 |

## 程序结构

```text
wallpaperengine@waylandwe/
  extension.js / wallpaperExtension.js / manager.js
  prefs.js / managerUi.js / resourceSetup.js
  common/paths.js
  helpers/dataWorker.py
  captureWorker.py / schemas/
  backend/linux-x86_64/bin/renderer
  backend/linux-x86_64/bin/linux-wallpaperengine
  backend/linux-x86_64/lib/
  backend/linux-x86_64/manifest.json
  package-manifest.json / LICENSE / NOTICE.md / licenses/
```

`common/paths.js` 根据安装位置确定后端路径；旧路径设置仅用于兼容迁移。运行不依赖源码、build、旧 runtime 或 Steam 进程。
共享库只用于后端进程，不污染 GNOME/GTK 的动态库搜索路径。宿主保留图形驱动、系统 ABI、GNOME、Python/GI 与字体。
当前 Debian 构建包含 215 个私有库，具体闭包以每个发行包清单为准；不是可以任意删除的独立可选文件。

## 首次使用与资源事务

首页引导分别选择公共 assets 和壁纸目录。后端、公共资源和图库有独立状态；无选择的空图库保持静态待配置，不误报已选文件丢失。
导入复制到 XDG 数据盘的暂存目录，校验文件、记录提交日志后完成切换；有写锁、进度和取消，拒绝符号链接逃逸、损坏入口和不支持的数据版本。
导入不自动选择壁纸或启动动态；重复条目跳过，不覆盖用户自定义静态图。旧 runtime 迁移保留原目录和原有选择/FPS/轮换设置。

## 播放和截图边界

静态模式由 GNOME 原生背景显示；概览和应用列表使用原生背景对象。没有后端、频谱采集和鼠标桥。
显式动态模式启动包内后端，按 Wayland 客户端归属识别窗口并放入背景层；沿用 Forge 排除、工作区焦点修复与合成保护。
高质量静态截图通过独立一次性任务以 4K 渲染后缩小到 1080p；任务完成或取消即退出，不改变常规播放 FPS 和分辨率。

## 安装、升级与回滚

统一安装器验证平台、执行能力、文件集合、权限与哈希。升级先等待自身播放/截图退出，暂存编译 schema，原子交换目录并保存旧目录。
不就地覆盖内存映射中的 schema 或程序。失败保留原安装；回滚不清理资源。回滚到旧 runtime 时使用旁边的设置快照恢复后端入口。
磁盘程序与 Shell 活动模块分开核验；正常用户重新登录加载新版，不依赖开发热更新入口。

## 构建身份、许可与验证

构建记录绑定渲染源码树和产物哈希；打包拒绝脏的程序输入、其他 checkout 的缓存及逃逸源码链接。
发行附带项目对应源码和精确 Debian 依赖源包，保留 portghost/Almamu、GNOME 上游及第三方许可。
验证包含系统依赖隔离、只读安装目录、隐藏旧源码/runtime、场景和视频集成、真实桌面升级，以及删除旧安装/构建后分别从安装包和源码首次安装。
两轮真实首次使用均由用户选择资源目录并确认画面和交互；同一 GNOME 会话通过显式入口更新缓存，未把这一过程冒充重新登录测试。

## 范围

首个二进制平台为 Debian 13、GNOME 48、Wayland、x86_64，最低 GLIBC 2.39。metadata 的其他 Shell 声明不代表已全部验证。
支持 scene/video，未打包完整 Web/CEF 运行能力。不会发布用户壁纸、截图或 assets；不会新增独立开机播放服务。

入口：[README](../README.md)、[开发说明](DEVELOPMENT.md)、[完整包安装](FULL-PACKAGE.md)、[验收记录](FRESH-INSTALL-VALIDATION.md)。
