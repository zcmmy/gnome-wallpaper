# 开发与发布

## 模块职责

- `renderer/source/`：资源解析、场景脚本、动画、音频频谱、OpenGL、Wayland 和通用 IPC。保留 portghost 固定来源与 GPL-3.0-only。
- `gnome/extension/`：窗口归属和背景层、静态原生背景、概览、指针桥、管理 UI、导入和截图生命周期。
- `integration/`：两层协议、集成测试及历史 runtime 工具。
- `packaging/`：完整包构建、运行库闭包、来源审计、原子安装、回滚和干净环境测试。

GNOME 不链接 C++ 库，IPC 不传送图像帧；后端以独立进程提交 Wayland surface。结构变化详见 [重构说明](REFACTORING-v0.1.0.md)。

## 开发环境和构建

使用 [安装文档](INSTALL.md) 中的系统开发依赖。普通开发不需要私有 `deps/`；可选的 `deps/sysroot/usr` 必须完整，配置损坏时直接报错。
源码包含上游 External 源码，无需初始化 submodule；首次 CMake 配置联网下载固定的 CEF 构建依赖。

```bash
make package-backend
make check
python3 gnome/tests/check-first-use-ui.py
```

默认产物位于 `build/package-renderer/output/`，构建记录为 `backend-build.json`。`BUILD_JOBS` 控制并行数；`WALLPAPER_BUILD_DIR` 选择构建目录。
构建目录只属于当前 checkout。移动源码位置或改用另一 worktree 时重新配置/构建，不修改 CMake 缓存来冒充原位置。

## 本地安装与组包

```bash
# 提交需要组包的源码及文档改动后：
make install
# 或仅生成包，目标必须不存在：
make extension DEST="$PWD/dist/local-package"
```

两种方式都校验源码树、已构建二进制和 Git 快照。`make install` 不重新编译，使用临时完整包调用正式安装器；安装结果没有源码链接。
`make extension-dev`、`make renderer` 和 `make package DEST=...` 是历史开发接口，不用于替代完整发行包。

## 验证层次

`make check` 涵盖 C++、GNOME、资源事务、安装/回滚、源码和许可检查。
首次使用图形测试单独运行，不自动导入真实资源或启动真实桌面播放。
`packaging/check-desktop.py <完整ZIP>` 验证私有 GNOME 会话，需自备测试资源；它覆盖静态/动态、鼠标 IPC、截图及桌面扩展兼容。
系统与用户验收边界见 [完整包验证](PACKAGING-VALIDATION.md)、[干净环境](CLEAN-ENVIRONMENT.md)和[全新安装](FRESH-INSTALL-VALIDATION.md)。

## 公开发行

所有发行输入必须已提交。先完成 dev → main 合并，并在最终提交上组包，使依赖清单、项目源码归档与版本标签对应。
后端源树未变化时可复用经过校验的后端构建；如果渲染源码发生变化则重新执行 `make package-backend`。

```bash
make extension DEST="$PWD/dist/source-index"
python3 packaging/fetch-sources.py dist/source-index/backend-manifest.json build/dependency-sources
WALLPAPER_DEPENDENCY_SOURCES="$PWD/build/dependency-sources" make release-package
cd dist/v0.1.0
sha256sum --check SHA256SUMS
```

已有精确依赖源码集合可直接复用；发行组包会核对每个源包版本、`.dsc`、归档大小和哈希。不同版本不能互换。
完整附件包括程序 ZIP、安装器、安装与验证说明、依赖清单、项目对应源码、依赖对应源码、获取工具和校验和。
源码归档不能包含用户资源、日志、内部文档、编译结果或开发机绝对链接。

锁定依赖的容器流程为 `packaging/container-build.sh`，仅供一次性 Debian 13 容器，不在用户宿主运行。
GitHub 的构建与发布工作流手动触发；发布工作流要求同提交的成功构建记录。人工发布也必须满足相同源码、校验和及验收要求。
版本、合并与标签规则见 [版本管理](VERSIONING.md)。

## 安全部署和当前会话

安装器暂存编译 schema，再原子交换目录，禁止原地截断活动 schema、可执行程序或共享库。
安装不等于当前会话已加载：GNOME 缓存模块，正常使用在下次登录生效。开发用 Looking Glass 入口必须先隔离测试、由用户显式执行；不作为普通安装步骤。
不要为部署重启、注销用户或改变其他扩展、桌面外观及启动项。保留用户自定义静态图和真实资源，所有生成物放在忽略目录中。
