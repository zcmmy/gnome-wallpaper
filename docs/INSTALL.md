# 安装与运行

仅安装或升级插件可使用 [Release 插件包](PLUGIN-INSTALL.md)。以下为完整源码与独立运行包流程。

## 1. 系统依赖

本地已验证 Debian 13 / GNOME 48 / Wayland / x86_64。
需要 Git、CMake、Ninja、pkg-config、C++20 编译器，及以下开发库：
OpenGL/EGL、GLFW、GLEW、GLM、SDL2、mpv、FFmpeg、PulseAudio、DBus、zlib、LZ4、FreeType、
Wayland、wayland-protocols、X11/XRandR、Fontconfig。部分桌面库也由 CEF 构建依赖使用。
Debian 系列可参考以下包名（按发行版调整；本仓库不自动执行安装）：

```text
build-essential cmake ninja-build pkg-config git libgl1-mesa-dev libegl1-mesa-dev
libglfw3-dev libglew-dev libglm-dev libsdl2-dev libmpv-dev libavcodec-dev
libavformat-dev libavutil-dev libavdevice-dev libswscale-dev libswresample-dev
libpulse-dev libdbus-1-dev zlib1g-dev liblz4-dev libfreetype-dev libfontconfig-dev libwayland-dev
wayland-protocols libx11-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev
libnss3 libnspr4 libxcomposite1 libxdamage1 libasound2t64
```

插件/UI/辅助截图需要 gnome-shell、gjs、python3、python3-gi、gir1.2-gtk-4.0、
gir1.2-adw-1、gir1.2-gdkpixbuf-2.0、libglib2.0-bin、dbus-daemon、dconf-cli。
以 CMake 的缺包诊断为准；不要求复制开发者个人 deps/sysroot。
CEF 版本固定于 sources.lock.json 和上游 CMake，构建时需要网络下载且占用较大空间。
ISPC 是上游可选的纹理压缩工具依赖，普通 scene 播放不要求单独启用该工具。

文字渲染使用壁纸自带字体，并通过 Fontconfig 补齐缺字。需要安装覆盖目标语言的系统字体；
Debian 可使用 `fonts-noto-cjk` 覆盖中日韩文字。它是系统字体依赖，不随项目发布用户字体。
多语言回归还需要 `fonts-dejavu-core`；其他发行版可用 `UNICODE_TEST_LATIN_FONT` 与
`UNICODE_TEST_CJK_FONT` 指定等效字体路径。详见 [多语言文字](UNICODE-TEXT.md)。

## 2. 用户资源（不要提交到 Git）

将合法持有的 Wallpaper Engine 安装目录 assets 复制到项目 assets/。
将已下载的 Workshop 壁纸目录放在 wallpapers/<ID>/，通常包含 project.json、scene.pkg 或视频。
可选静态图命名为 static-background.png；用户提供的静态图优先，不会自动覆盖。
当前预览、历史测试和运行包仍需要 wallpaper/ 兼容样本目录：从自己的场景壁纸完整复制一份。
无权再分发的壁纸、静态图、音频、字体和 WE assets 均不进入源码发布。

## 3. 构建与生成运行包

```text
make renderer
make extension
make check
make package DEST="$HOME/.local/share/gnome-wallpaper-runtime"
```

目标必须尚不存在；已有运行目录应先备份，再向新目录打包，避免覆盖用户图库。
bin/check-runtime 验证动态库与资源是否齐全；运行包只覆盖 scene/video 使用路径。

## 4. 显式安装和配置

设 RUNTIME 为上一步生成的绝对路径，运行：

```text
"$RUNTIME/bin/check-runtime"
"$RUNTIME/bin/install-gnome"
"$RUNTIME/bin/configure-gnome"
```

configure-gnome 会写入该运行包的路径并重置动态/轮换为关闭、FPS 为 15。初始化脚本清空当前素材选择。
请在管理界面选择自己导入的壁纸；项目不提供素材或其信息。不要在已有配置上无意重复执行此初始化命令。
新安装扩展若未被当前 Shell 发现，在方便时重新登录；脚本不会自动注销或重启。

```text
gnome-extensions enable wallpaperengine@waylandwe
"$RUNTIME/bin/manager"
```

扩展管理器的开关控制整个插件；管理界面中的“动态模式”控制渲染器。
标准扩展启用列表属于 GNOME 持久配置，后续登录可能自动恢复该扩展；本项目不创建独立启动服务。
不要将开发期 apply-*.js Looking Glass 迁移脚本作为常规安装步骤。

## 5. 停止与恢复

在管理界面关闭动态模式即可停止渲染并保留原生静态壁纸。

```text
gnome-extensions disable wallpaperengine@waylandwe
```

可关闭整个扩展；需要恢复首次启用前原生背景时，再执行运行包 bin/restore-background。
静态图库和回收站属于用户数据，卸载扩展时不要一并删除。

## 6. 安全更新

插件必须通过 install-extension.py / bin/install-gnome 原子交换目录。
不要原地覆盖正在映射的 gschemas.compiled，也不要在活动扩展目录重新编译 schema。
替换二进制和共享库应通过临时文件加原子重命名；当前会话代码不会因为磁盘变化而自动重载。
