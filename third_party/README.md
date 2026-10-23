# 上游引用、依赖和许可

本项目是独立的下游集成。**核心渲染技术来自 portghost 及其上游 Almamu**，不是本项目从零实现的引擎。
项目原创代码及修改采用 **GPL-3.0-only**；完整条款见 [LICENSE](../LICENSE)，归属和例外见 [NOTICE.md](../NOTICE.md)。

## portghost：直接使用的渲染器

| 项目 | 引用 |
| --- | --- |
| 仓库 | [portghost-dev/linux-wallpaperengine](https://github.com/portghost-dev/linux-wallpaperengine) |
| 固定基线 | [`50530e5167c0822e63f052f50ef8d8613663915a`](https://github.com/portghost-dev/linux-wallpaperengine/tree/50530e5167c0822e63f052f50ef8d8613663915a) |
| 本地源码 | [renderer/source](../renderer/source) |
| 上游说明 | [下游范围与原始 README 引用](../renderer/source/README.md)、[架构](../renderer/source/ARCHITECTURE.md) |
| 许可证 | [原始 GPLv3 全文](../renderer/source/LICENSE)；[Arch 配置](../renderer/source/packaging/archlinux/PKGBUILD) 标注 `GPL-3.0-only` |
| 来源记录 | [sources.lock.json](sources.lock.json)、[v0 初始修改索引](local-changes-v0.json) |

我们以纳入顶层 Git 的渲染器源码保存该基线与本地修改，避免引用开发机独有的 submodule 提交。
当前快照已裁剪未使用的 UI 与演示资源；固定 commit/tree 仍记录原始导入基线，不伪称为裁剪后树的哈希。
锁文件中的 commit 是**上游基线**，实际集成版本由顶层 Git 提交标识；不能把修改后源码称为未经修改的上游版本。

### 上游提供的能力

- Wallpaper Engine 场景/纹理资源解析、OpenGL 绘制与媒体支持。
- 场景动画、脚本、粒子、光影和特效管线。
- 音频反应、视差、输入和本地控制接口的基础实现。

### 本项目的增量

- 独立的 GNOME Shell 窗口嵌入、概览/应用列表背景与桌面指针桥。
- 频谱分组、外部鼠标坐标及视频纹理兼容修复。
- 一次性 4K 场景渲染缩小为 1080p 的静态截图与取消回收。
- 静态优先图库、导入/删除、动态开关、全局 FPS、轮换和独立运行包。

这些改动不替代对上游工作的归属。完整差异以本项目源码和 Git 历史为准。

## Almamu 与上游贡献者

portghost 扩展自 [Almamu/linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine)。
感谢 Almamu、portghost 和所有上游贡献者；portghost README 中对 ian-vinson、Haberno、
Intel ISPC Texture Compressor 等工作的致谢完整保留，不将这些贡献归为本项目原创。
`sources.lock.json` 的 `renderer_ancestor.reference_commit` 是早期研究记录，不代表 portghost 的合并基点。

## GNOME 扩展来源

基于 [diaslucass/wallpaperEngineWayland](https://github.com/diaslucass/wallpaperEngineWayland)，固定基线
[`e2ae60dc89a18235f315aee9dcca6a3b6fe89fa4`](https://github.com/diaslucass/wallpaperEngineWayland/tree/e2ae60dc89a18235f315aee9dcca6a3b6fe89fa4)。
[上游 README 的 License 部分](../gnome/extension/README.md#license) 明确使用 `GPL-2.0-or-later`。
本项目保留原声明，修改版本按 GPLv3 分发；原始代码的 GPL-2.0-or-later 授权不被撤销。
GNU 的[GPLv3 指南](https://www.gnu.org/licenses/quick-guide-gplv3.html)说明了 GPLv2-or-later 与 GPLv3 的兼容关系。

## 传递依赖及许可例外

[External](../renderer/source/src/External) 中的 Catch2、argparse、MimeTypes、ISPCTextureCompressor、
kissfft、SPIRV-Cross-WallpaperEngine、json、quickjs、stb 和 glslang-WallpaperEngine 随 renderer 基线固定。
它们保留各自许可；[licenses.json](licenses.json) 索引这些文件，不能统一改写为 GPL。
未使用的上游 `lwe-ui`、其测试（含 40 个 `.lwebackup` 夹具）、7 张演示图片/动图及专用 `install.sh` 已移除。
其原始 [MIT 声明](https://github.com/portghost-dev/linux-wallpaperengine/blob/50530e5167c0822e63f052f50ef8d8613663915a/lwe-ui/pyproject.toml) 仅作为历史来源；本项目管理 UI 位于 `gnome/extension/`。
C++ 测试实际使用的一份帮助输出文本已移到 renderer 测试目录；内容与 GPL 渲染器中的字符串一致。
External 依赖的测试、许可证和自建合成校准工具保留，不把它们误认为用户壁纸资源。
历史 `v0` 修改索引、标签和提交保持原状，不代表当前文件清单。

额外归属、构建脚本许可和头文件/协议许可见 [组件说明](COMPONENT-NOTICES.md)。

CEF 固定版本和下载入口见锁文件，构建时按上游 CMake 下载；系统 OpenGL、GLFW、FFmpeg、mpv、GNOME 等由发行版提供。
系统库不由上游 commit 锁定。安装需求见 [INSTALL.md](../docs/INSTALL.md)。
运行包保留项目许可证、归属说明以及已取得的库许可证；发行者仍需满足完整对应源码等许可要求。

## 用户资源

Wallpaper Engine assets、Workshop 场景、视频、字体和用户截图不在项目 GPL 授权范围内，也不随源码上传。
项目不是 Wallpaper Engine 官方产品，与其权利人不存在所暗示的关联或背书。
