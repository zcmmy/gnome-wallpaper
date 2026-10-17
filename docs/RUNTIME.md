# Wallpaper scene runtime — Debian 13 x86_64 / GNOME Wayland

此目录可整体移动，不依赖 wallpaper_adapter 的源码、构建目录或 deps/sysroot。
用途：本地场景与视频壁纸管理，静态背景、按需动态、全局帧率及定时轮换。
运行 bin/manager 打开管理窗口；默认静态、15 FPS、关闭轮换。
未包含 Chromium/CEF、网页服务与网页壁纸资源；不支持 Web 类型壁纸。
系统需提供 glibc、C++ 运行库、Mesa/OpenGL、Wayland、FFmpeg、PulseAudio/PipeWire 等共享库，
完整依赖名称见 manifest.json。它是当前系统的独立运行目录，不是跨发行版静态程序。

## 目录

```text
bin/        相对路径启动、检查及手动配置命令
libexec/    C++ 渲染器
lib/        渲染核心库及系统缺少的私有运行库
assets/     WE 公共资源
wallpapers/ 壁纸库、预存静态图与缩略图
wallpaper/  旧版单壁纸预览资源（兼容）
gnome/      可安装的 GNOME 插件（含已编译 schema，revision 12）
licenses/   许可证说明
```

## 独立预览（在任意工作目录执行）

```text
/此目录/bin/check-runtime
/此目录/bin/preview
```

关闭预览窗口或终端 Ctrl+C 即可退出。
启动脚本不会创建源码路径软链接，不需要 Steam 登录；缓存使用系统 XDG 用户目录。

## GNOME 部署（手动执行）

```text
/此目录/bin/install-gnome
/此目录/bin/configure-gnome
```

安装器暂存完整新版本并原子交换目录，保留旧版备份；不会修改设置或启用扩展。
禁止原地覆盖已加载的 gschemas.compiled，也不要在活跃扩展目录中重新编译 schema。
GNOME Wayland 已缓存旧模块时，需要注销后重新登录才能加载新版；之后手动启用插件。
注意：常规 gnome-extensions enable 会记住启用状态，后续登录也会启用。
如仍要求仅当前会话运行，请沿用显式的 Looking Glass 会话加载方式，不执行常规 enable。
切换壁纸先应用 wallpapers/<ID>/static-background.png；仅明确开启动态后启动后端。
已有静态图不会自动覆盖。缺图时明确开启动态，会辅助截图一次并应用。
可从界面选择图片覆盖静态图；动态模式沿用到后续切换，重新登录默认静态。
轮换默认为关闭、30 分钟、全部已准备壁纸，支持顺序和一轮内不重复的伪随机序列。
关闭播放后保留静态壁纸。恢复原壁纸：执行 bin/restore-background。
原配置保存在 ~/.local/state/wallpaper-adapter/original-background.json。
移动运行目录后重新执行 configure-gnome，以更新 GNOME 保存的资源绝对路径。
不要单独移走 bin/ 或 lib/；移动整个目录。

本目录只用于本机运行；用户提供的 WE 公共资源和 Workshop 壁纸并未被授予再分发许可。

壁纸库数量由当前目录内容决定。管理界面支持“导入壁纸…”和“删除壁纸…”。
导入可选择单张目录或含多张 project.json 子目录的目录，支持 scene/video；复制到运行库，不修改来源，同名跳过。
导入时不启动渲染器；已有静态图会一起复制，缺图仍由用户显式开启动态后辅助生成。
删除会先确认再移入系统回收站，删除当前播放项会先切换并等待旧渲染器退出。
删除最后一张会关闭动态与轮换，保留原生静态背景。当前运行库内的操作不会删除导入来源。

## 高质量静态图

```text
bin/capture-static --scene /壁纸目录 --output /输出图片.png
```

默认 scene 使用 4K 可见区域渲染后缩小为 1920×1080；video 从原生解码帧缩放。
这是一次性任务，依赖本机 python3-gi/GdkPixbuf、gnome-shell、dbus-run-session 与 gdbus。
使用私有合成器、DBus 和配置目录，完成或取消后退出；日常动态播放参数不变。
缺图时显式开启动态才自动调用该任务，不覆盖用户已有静态图片。
静态模式下概览/应用列表使用当前原生壁纸，退出菜单释放额外背景层，不启动渲染器。

## 开源许可

项目采用 GPL-3.0-only，目录内的 `LICENSE` 和 `NOTICE.md` 保存完整条款及来源说明；在线版本见[许可证](https://github.com/zcmmy/gnome-wallpaper/blob/main/LICENSE)和[归属声明](https://github.com/zcmmy/gnome-wallpaper/blob/main/NOTICE.md)。
运行包中的用户壁纸、WE assets 和单独许可的库不因此被重新许可。

## 动态播放时手动更新静态图

在壁纸库选中当前正在播放的壁纸，点击“高质量截图并替换静态图…”，确认后后台另开一次截图任务。
场景以 4K 渲染并缩小至 1920×1080；视频按原生帧采样至 1920×1080，与缺图自动生成共用高质量流程。
截图成功后覆盖这张壁纸已有的静态图（包括用户自行提供的图片），并更新缩略图和 GNOME 原生背景。
动态播放进程继续运行，FPS、频谱和鼠标设置不变。额外截图进程仅任务期间存在，会产生短暂额外 CPU/GPU 和内存负载。
独立任务从壁纸初始状态渲染，截图时刻可能与桌面不同；不捕获当时鼠标视差或实时音频频谱。
静态模式、加载中、选择了其他壁纸或已有截图任务时按钮不可用。
换图、停止动态、禁用插件会取消任务并回收私有截图进程；截图失败或期间静态图被其他操作修改时保留原图。
此入口需要更新插件，复用已有支持高质量截图的渲染器，无新增截图 IPC 或常驻服务。
