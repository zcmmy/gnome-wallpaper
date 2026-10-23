# 第三方组件归属与许可补充

本文件补充 [NOTICE](../NOTICE.md)、[上游来源](README.md) 与 [许可证索引](licenses.json)。
原作者版权、文件内声明及各组件原始许可证均保留。未列明的许可例外仍以对应源文件为准。

## 随渲染器纳入的源码

下表各组件都随 portghost 固定基线 `50530e5167c0822e63f052f50ef8d8613663915a` 纳入。
其准确内容由该基线和本项目 Git 历史确定，不为 vendored 目录虚构独立版本号或提交。

| 组件与源码位置（相对 renderer/source/src/External） | 归属/来源 | 许可与用途 |
| --- | --- | --- |
| `glslang-WallpaperEngine` | Khronos Group 及许可证内所列作者；portghost 集成的修改版 | BSD/MIT/Apache 等多许可；着色器编译，见其 LICENSE.txt |
| `SPIRV-Cross-WallpaperEngine` | Khronos Group、SPIRV-Cross 贡献者；修改版 | Apache-2.0 及 Khronos 文件级许可；见 LICENSE 与 LICENSES |
| `kissfft` | Mark Borgerding 及贡献者 | BSD-3-Clause；频谱处理，工具/测试另有例外 |
| `quickjs` | Fabrice Bellard、Charlie Gordon、QuickJS-NG 贡献者 | MIT；场景脚本 |
| `argparse` | Pranav Srinivas Kumar 与贡献者 | MIT；命令行参数 |
| `json` | Niels Lohmann 与贡献者 | MIT 主库；测试资料另含 BSD/Apache/GPL 等声明 |
| `MimeTypes` | Lasse Lukkari | MIT；资源类型识别 |
| `stb` | Sean Barrett 与贡献者 | MIT 或 Unlicense；测试图片须另查自身许可 |
| `Catch2` | Martin Hořeňovský、Phil Nash 与贡献者 | BSL-1.0；测试，不是桌面运行依赖 |
| `ISPCTextureCompressor` | Intel Corporation 与贡献者 | MIT；可选纹理压缩构建工具 |

上游贡献与这些组件的具体版权行以 [原始 External 树](https://github.com/portghost-dev/linux-wallpaperengine/blob/50530e5167c0822e63f052f50ef8d8613663915a/src/External)
及本地许可证索引为准。`stb/tests/pngsuite/PngSuite.LICENSE` 已独立列入索引，
不能把所有测试图片一概按 stb 主许可证处理。

## External 目录外的许可

- **CallStack**：Jun Zhang，2017，BSD-3-Clause；源码
  `renderer/source/src/WallpaperEngine/Debugging/CallStack.h/.cpp` 保留完整声明。
  [原项目](https://github.com/ZhangJunQCC/CallStack-for-Windows-and-Linux)；
  另保存 [原文副本](licenses/CallStack-BSD-3-Clause)，便于分发时携带。
- **CMake 辅助脚本**：作者和许可全文见 [模块说明](../renderer/source/CMakeModules/README.md)。
  这些构建工具的 BSD 授权与渲染器 GPL 授权分别保留。
- **GLM**：G-Truc Creation，MIT/Expat；当前本机构建使用 `0.9.9.8` 头文件。
  [Debian 版权原文](licenses/libglm-dev-copyright) 从本机对应 sysroot 包保存；
  [上游](https://github.com/g-truc/glm)。即使不出现在 `ldd` 中，编入二进制的头文件代码也需保留声明。
- **Wayland 协议**：源码 `renderer/source/protocols/*.xml` 各自保留完整版权和许可；
  另外构建生成的 xdg 协议来自系统 wayland-protocols，
  [Debian 声明](licenses/wayland-protocols-copyright) 从当前 sysroot 保存。
  [上游](https://gitlab.freedesktop.org/wayland/wayland-protocols)；生成代码里的声明不可删除。
- **CEF**：版本与获取入口见 [锁文件](sources.lock.json)。本次补入的是 CEF 自有代码的 BSD 许可证，
  不代表 Chromium 全部第三方许可。现有 scene/video 运行包未携带完整 CEF Web 运行时。

## 分发边界

本次移除的是未使用的 UI、UI 测试资料、混合安装脚本和演示图；保留有效的 C++ 测试、
合成校准工具与依赖源码。没有删除用户 assets、图库或运行目录，也没有重写历史标签。
`local-changes-v0.json` 只描述 v0 导入时的历史变化，不能作为当前打包文件清单。

此索引覆盖源码声明，不等于二进制发行的合规结论。现有独立运行包脚本已补充静态库/头文件及构建依赖的声明索引、
实际 sysroot 包版权、Wayland 生成代码声明和 Debian 声明引用的通用许可全文。
缺少声明或出现未登记的私有库时会中止打包，避免静默遗漏。
这只完善原有运行包的 `licenses/`，不改变运行架构；现有安装和历史发行产物不会因此改变。
完整后端发行前仍须：

- 核对实际构建与声明集合一致；新增静态链接/头文件代码、协议或私有动态库时更新收集规则，不能只检查 `ldd`。
- 核实 FFmpeg、mpv 等的实际编译选项和包版本；不能一概写成 LGPL。
- 提供适用 GPL/LGPL 的完整对应源码、修改和构建材料；仓库链接或版权声明本身不能替代这些义务。
- 变更系统依赖时同步核验声明；本机保存的 GLM、Wayland 包声明不锁定所有用户的系统包版本。

Wallpaper Engine assets、用户壁纸与截图不因开源渲染器而获得再分发授权；本项目不提供这些资源。
