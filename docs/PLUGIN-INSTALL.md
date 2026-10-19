# GNOME Wallpaper v0.0.2 插件安装

> 本文对应已发布的 v0.0.2 安装包。当前源码已更新为 v0.0.3，但本次不发布 Release 附件；
> v0.0.2 下载包不含多语言文字与工作区焦点修复。源码升级范围见 [v0.0.3 版本说明](releases/v0.0.3.md)。

## 下载与校验

从 [v0.0.2 Release](https://github.com/zcmmy/gnome-wallpaper/releases/tag/v0.0.2) 下载以下四个文件到同一空目录：

- `gnome-wallpaper-v0.0.2.shell-extension.zip`：GNOME 插件、辅助脚本、schema、版本和许可证。
- `install-extension.py`：原子安装器。
- `INSTALL-v0.0.2.md`：本文的离线副本。
- `SHA256SUMS`：上述三个文件的 SHA-256 校验值。

在下载目录运行：

```bash
sha256sum --check SHA256SUMS
```

ZIP 不包含 C++ 渲染器、第三方动态库、壁纸、静态截图或 Wallpaper Engine assets。
这是 GNOME 插件包，不是完整的独立运行包。已有 v0.0.1 后端可继续使用；
新用户需按 [完整安装说明](https://github.com/zcmmy/gnome-wallpaper/blob/v0.0.2/docs/INSTALL.md) 构建后端并准备合法自备资源。

## 依赖和安装

本地验证：Debian 13、GNOME 48、Wayland、x86_64。metadata 声明的其他 Shell 版本未全部验证。
插件需要 GJS、Python 3、PyGObject、GTK 4、Libadwaita、GdkPixbuf、GLib schema 工具和 dconf。
安装命令还需要 unzip；发行版包名见完整安装说明。

校验通过后，在下载目录执行：

```bash
stage=$(mktemp -d)
unzip -q gnome-wallpaper-v0.0.2.shell-extension.zip -d "$stage"
python3 install-extension.py "$stage" "${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/wallpaperengine@waylandwe"
rm -rf -- "$stage"
```

安装器在暂存目录编译 schema，再原子交换整个插件目录；已安装的旧目录保存为相邻的 `.wallpaper-backup-*`。
它不写入 GSettings、不启用扩展、不启动渲染器、不注销或重启桌面。
已有 UUID 保持不变，原有图库路径、选择、FPS 和界面设置保留。
不要直接解压覆盖活动插件目录，也不要在其中重新编译 `gschemas.compiled`。

磁盘更新不会替换 GNOME 已缓存的模块。请在方便时自行重新登录，以加载磁盘中的新版代码。
首次安装如尚未被 Shell 发现，也需要重新登录。随后按需执行：

```bash
gnome-extensions enable wallpaperengine@waylandwe
gnome-extensions prefs wallpaperengine@waylandwe
```

管理界面的路径设置允许指定壁纸库、portghost 可执行程序和公共 assets。
先从图库选择用户自己的壁纸；新安装没有预选素材。静态模式直接使用已有的 `static-background.png`。
需要动态时明确开启“动态模式”；缺少静态图时可通过动态模式生成一次高质量静态图。
管理器的新登录行为保持静态优先，不因更新自行开始动态播放。
GNOME 可以记住扩展的启用状态；本包不添加独立的开机启动服务。

## 升级范围与回退

v0.0.2 修复动态壁纸在空工作区遮挡顶栏与 Dock 的合成问题，C++ 渲染器相对 v0.0.1 没有改动。
动态期间抑制合成器的直接扫描输出，可能增加合成成本；静态模式释放该引用。
详情见 [版本说明](https://github.com/zcmmy/gnome-wallpaper/blob/v0.0.2/docs/releases/v0.0.2.md)。
需要回退时，使用同一安装器，把上次输出的备份目录作为 source，当前插件目录作为 destination；
在下次登录加载回退代码。用户图库及静态图不属于插件安装目录，不随安装或回退删除。

项目按 GPL-3.0-only 发布，ZIP 包内包含 LICENSE、NOTICE.md。
[固定上游来源与许可](https://github.com/zcmmy/gnome-wallpaper/blob/v0.0.2/third_party/README.md) 包括 portghost、Almamu 和 GNOME 扩展上游；素材权利不属于项目许可证。
