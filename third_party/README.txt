上游与第三方依赖

固定基线见 sources.lock.json；本仓库保留修改后的完整源码快照。
这份锁文件记录来源，不表示上游未修改，也不声称已经锁定发行版动态库的二进制版本。

渲染器
https://github.com/portghost-dev/linux-wallpaperengine
commit 50530e5167c0822e63f052f50ef8d8613663915a
路径 renderer/source；GPL v3 文本在 renderer/source/LICENSE。
源自 https://github.com/Almamu/linux-wallpaperengine；保留原文件作者信息和许可证。
本项目补丁涉及 GNOME 窗口输入、频谱、视频纹理和高质量静态截图。

GNOME 扩展来源
https://github.com/diaslucass/wallpaperEngineWayland
commit e2ae60dc89a18235f315aee9dcca6a3b6fe89fa4
路径 gnome/extension；在此基线上增加图库管理、静态模式、截图任务、概览和原子部署。
该锁定上游快照没有独立 LICENSE 文件，本项目没有替它声明新许可证。
此仓库不宣称所有目录统一适用某一许可证；第三方代码保留各自的声明。

渲染器已携带的 External 源码
renderer/source/src/External 下的 Catch2、argparse、MimeTypes、ISPCTextureCompressor、
kissfft、SPIRV-Cross-WallpaperEngine、json、quickjs、stb、glslang-WallpaperEngine
均随上述 renderer commit 固定；保留其 LICENSE/COPYING/LICENSES 与文件内声明。
许可证索引见 licenses.json；未单独提供独立 Git commit 的部分以渲染器 tree 为来源。

下载及系统依赖
CEF 固定版本见锁文件；下载地址与验证逻辑保留在 CMakeModules/DownloadCEF.cmake。
系统 OpenGL、GLFW、GLEW、FFmpeg、mpv、PulseAudio、Wayland、GNOME、GTK 等由系统提供。
完整依赖及安装流程见 docs/INSTALL.txt。打包仅复制解析到的本地私有库并记录系统库列表。
独立包 licenses/ 保存渲染器许可和可取得的私有库声明；源码发布不附带这些二进制。

用户资源
Wallpaper Engine assets、Steam Workshop 场景、视频和用户静态图不属于本仓库源码。
它们由用户另行准备，不能从本仓库 clone 得到，也不会进入 v0 提交。
