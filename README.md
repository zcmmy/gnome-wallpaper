# GNOME Wallpaper — v0.1.0

GNOME Wayland 上的 Wallpaper Engine 场景和视频壁纸管理器，使用独立的 portghost C++ 渲染器。
**v0.1.0 提供完整预编译安装包**：后端、必要私有库、GNOME 插件及管理界面一起安装，用户通过界面导入自己的 assets 和壁纸。

验证平台：**Debian 13 / GNOME 48 / Wayland / x86_64**。预编译安装器按此平台检查，不是跨发行版通用二进制。
项目不提供任何壁纸、Wallpaper Engine assets、用户截图或素材下载信息。

## 通过安装包安装

从 [v0.1.0 Release](https://github.com/zcmmy/gnome-wallpaper/releases/tag/v0.1.0) 下载以下三个文件到同一目录：

- `gnome-wallpaper-v0.1.0-linux-x86_64.shell-extension.zip`
- `install.py`
- `SHA256SUMS`

在下载目录执行：

```bash
sha256sum --check --ignore-missing SHA256SUMS
python3 install.py ./gnome-wallpaper-v0.1.0-linux-x86_64.shell-extension.zip
```

安装器校验平台、依赖和包完整性，在暂存目录准备后原子安装；升级时停止本插件的播放/截图并保留旧程序供回滚。
无需编译、手动解压、部署 runtime 或填写后端路径。不要直接解压覆盖活动插件目录。
系统仍需 GNOME、图形驱动、GJS、Python/PyGObject、GTK4、Libadwaita 和字体；完整依赖见 [安装说明](docs/INSTALL.md)。

Release 中的两份对应源码归档、依赖清单和验证文档供审计与重建使用，正常安装不需要下载源码归档。

## 通过源码构建并安装

先按 [构建依赖](docs/INSTALL.md#源码构建依赖) 安装系统开发工具和库，再执行：

```bash
git clone --branch v0.1.0 https://github.com/zcmmy/gnome-wallpaper.git
cd gnome-wallpaper
make package-backend
make check
make install
```

`make package-backend` 从源码编译后端，首次构建需要联网下载固定版本的 CEF 构建依赖；发行程序不携带完整 CEF Web 后端。
`make install` 使用已有构建临时组装完整包，再调用同一个原子安装器；不把源码软链接到安装目录。
默认并行数为 4，可用 `BUILD_JOBS=2 make package-backend` 调整。

只生成可分发安装包、不安装时执行：

```bash
make extension DEST="$PWD/dist/local-package"
```

目标目录必须不存在。自定义构建目录通过 `WALLPAPER_BUILD_DIR` 设置，构建和打包时使用同一值。
修改过程序后需先提交相关文件，再组包；打包器校验 Git 源码快照、构建记录和二进制哈希。
向他人发布二进制时，还需提供对应源码和依赖许可材料，见 [开发说明](docs/DEVELOPMENT.md)。

## 首次启用和资源导入

安装不会自动启用扩展、添加启动项或重启桌面。GNOME 尚未发现新扩展，或当前会话缓存了旧代码时，请在方便时重新登录，然后执行：

```bash
gnome-extensions enable wallpaperengine@waylandwe
gnome-extensions prefs wallpaperengine@waylandwe
```

1. 在首页“首次使用”中选择自己的公共 assets 目录和壁纸文件夹，确认后复制导入；来源文件保持不变。
2. 选择一张壁纸并点击“应用”。已有 `static-background.png` 时直接使用静态模式。
3. 需要动画时明确打开动态开关。默认上限 15 FPS，后续切换沿用动态意图，直到关闭；新登录保持静态优先。

没有静态图时，可提供自己的图片，或明确开启动态后生成一次 4K 渲染缩小至 1080p 的静态图。
动态播放时也可手动触发独立高质量截图，不中断日常播放、不改变日常分辨率或 FPS。
正式使用不需要 Looking Glass；开发会话更新入口仅用于测试。

## 功能与边界

- 静态缩略图和大图预览、导入、删除、切换，以及用户自定义静态图片。
- 静态模式不运行渲染器、频谱采集或鼠标桥；动态通过 Wayland surface 合成。
- 全局帧率上限、默认关闭的定时轮换、顺序或伪随机序列。
- 兼容普通桌面、概览、应用列表和工作区切换，保留 Forge、焦点及空工作区合成修复。
- 使用 Fontconfig 为缺失字形回退；中文、日文和韩文需系统中安装覆盖这些语言的字体。
- 目标为 scene/video；不包含完整 Web/CEF 壁纸运行依赖，也不承诺所有特效或视频编解码组合。

## 安装位置与更新

| 内容 | 默认位置 |
| --- | --- |
| 插件、后端和私有库 | `~/.local/share/gnome-shell/extensions/wallpaperengine@waylandwe/` |
| assets、壁纸、静态图和图库索引 | `~/.local/share/gnome-wallpaper/` |
| 可重建缓存 | `~/.cache/gnome-wallpaper/` |
| 日志、恢复和迁移状态 | `~/.local/state/gnome-wallpaper/` |

遵循 XDG 路径配置；源码、build、发行包、已安装程序和用户资源相互分离。
程序更新或卸载不删除用户资源。旧 runtime 用户可在设置中使用“迁移旧版资源”；先保留旧目录，迁移不自动播放。
升级、回滚说明见 [完整包管理](docs/FULL-PACKAGE.md)。

## 源码与文档

`renderer/` 为 C++ 渲染层，`gnome/` 为 Shell/管理界面，`integration/` 为协议和集成测试，
`packaging/` 为构建、依赖审计、安装和发布工具。`build/`、`dist/`、用户资源及个人报告不进入 Git。

- [开发与构建](docs/DEVELOPMENT.md)
- [v0.1.0 项目重构](docs/REFACTORING-v0.1.0.md)
- [运行架构](docs/ARCHITECTURE.md)
- [验证入口](docs/VERIFICATION.md)与[两轮全新安装验收](docs/FRESH-INSTALL-VALIDATION.md)
- [v0.1.0 版本说明](docs/releases/v0.1.0.md)与[更新记录](CHANGELOG.md)
- [版本管理](docs/VERSIONING.md)与[上游来源](third_party/README.md)

## 开源许可

本项目原创代码和修改采用 **GPL-3.0-only**，继承 portghost 的开源许可；见 [LICENSE](LICENSE) 和 [NOTICE.md](NOTICE.md)。
渲染器基于 [portghost-dev/linux-wallpaperengine](https://github.com/portghost-dev/linux-wallpaperengine)，固定基线为
[`50530e5167c0822e63f052f50ef8d8613663915a`](https://github.com/portghost-dev/linux-wallpaperengine/tree/50530e5167c0822e63f052f50ef8d8613663915a)，保留 Almamu 等上游归属。
GNOME 层基于 [diaslucass/wallpaperEngineWayland](https://github.com/diaslucass/wallpaperEngineWayland)。
第三方例外、版本与依赖对应源码说明见 [第三方引用](third_party/README.md)。项目许可证不授予任何用户素材的权利。
