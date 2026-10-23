# 安装与运行

新架构使用 [完整插件包](FULL-PACKAGE.md)：后端随包安装，资源在界面导入，不再配置 runtime 路径。
以下依赖说明供开发者构建使用；后面的独立运行包步骤保留为旧版开发流程，不能代替新架构的安装器。

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

## 2. 用户资源

正常使用时，在完整插件的管理界面导入自备公共 assets 与壁纸，不需要将资源放到源码仓库。
它们保存在标准用户数据目录，程序更新不删除资源或用户静态图。
源码中的 assets/、wallpapers/、wallpaper/ 仅供旧版开发工具和私人测试，Git 忽略这些目录。

## 3. 构建、打包与安装

从源码进行完整包构建，使用以下流程：

```bash
make package-backend
make check
# 将需要打包的程序和文档改动提交到 Git，保持源码快照与安装内容一致。
make extension DEST="$PWD/dist/local-package"
python3 dist/local-package/install.py dist/local-package/gnome-wallpaper-v0.0.3-linux-x86_64.shell-extension.zip
```

已有通过构建记录检查的后端时，可以直接执行 `make install`。
它在临时目录组包，再调用完整包原子安装器；不会重新编译，不依赖源码软链接运行，也不会自动启用扩展。
自定义构建位置可设置 `WALLPAPER_BUILD_DIR`，但不得借用其他 checkout 的构建缓存。
新架构完整说明见 [完整包安装与数据管理](FULL-PACKAGE.md)。

## 4. 历史开发入口

`make renderer`、`make package DEST=...` 和 runtime/bin 下的配置工具保留供旧版独立 runtime 开发使用。
`make extension-dev` 只生成 JS/Python 开发包，不能替代包含 C++ 后端的完整包。
这些入口的旧流程见 [独立运行包](RUNTIME.md)，不用于升级当前完整插件。
`gnome/scripts/install-extension.py` 拒绝覆盖已安装的完整包；正式安装使用 `make install` 或完整包附带的 `install.py`。
