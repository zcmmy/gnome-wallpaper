# 验证入口与预期结果

## 快速检查

```text
make check-renderer         频谱、指针/IPC、视频纹理、截图重采样
make check-gnome            静态背景、管理器、导入删除、生命周期、包完整性、schema 原子更新
make check                  上述两套检查与测试目录清理安全检查
```

C++ 测试需要现有构建；GNOME 检查不编译 C++，不启用实际桌面插件。

## 图形集成（需要 GNOME、GJS、图形设备和现有壁纸资源，运行时有短暂额外负载）

```text
make check-integration      现有输入/Wayland 桌面嵌入检查
make check-overview         静态应用列表、切图、动态交接、反复开关、禁用清理
make stage-manager
bash runtime/manager-test/run-test.sh
make stage-ui
bash runtime/manager-ui-test/run-test.sh
```

管理器日志需包含 MANAGER-TEST complete；UI 需包含 UI-TEST PASS，不应出现对应 ERROR。
两个 staging 命令均可在清理测试目录后独立运行。配置、DBus、显示均隔离于实际桌面。
static-overview 测试会复制当前安装的 Blur my Shell / Dash to Dock 和配置进行兼容检查。

## 截图与运行包

```text
python3 integration/tests/check-hq-worker.py       取消任务与子进程回收
python3 integration/tests/check-capture-runtime.py 生成截图诊断，不安装静态图
python3 integration/tests/regenerate-hq.py         开发图库批量生成到 reports/hq-capture/library，不覆盖用户库
python3 integration/tests/check-runtime-bundle.py /运行目录
```

真实截图以解码后的 PNG 尺寸和原始 FBO/UV 诊断验证，不能仅凭文件名判断 4K。
--freeze 与关闭视差用于独立对照；粒子、时钟脚本等不保证逐像素确定性。
运行包验证包含迁移路径及屏蔽整个开发目录的运行检查。

## 产物与清理

结果保存在 reports/；测试配置、缓存和复制资源保存在 runtime/<测试名>/。
make clean-tests 查看白名单清理计划；make clean-tests-apply 只删除未被进程引用的这些生成物。
测试失败先看报告，不要删除原始壁纸、构建依赖、回滚备份或当前会话模块。

## 干净 clone

make check-gnome 会在临时目录生成纯色 PNG 和编译 schema，不需要私人壁纸或已安装插件。
make check-renderer 中视频纹理测试需要已有后端构建；可先 make package-backend。默认检测 build/renderer、build/package-renderer，兼容旧 build/portghost；自定义目录通过 WALLPAPER_BUILD_DIR 指定。
图形集成和截图对照保留了开发图库的 ID/场景约定，需要自备匹配素材，不能当作无素材 CI。
check-static-overview 还需要本机装有 Blur my Shell 和 Dash to Dock；它们不是正式运行的强制依赖。

## 动态播放期间高质量截图测试

- `make check`：覆盖成功、原图并发修改保护、重复请求、取消及静态状态保护。
- `python3 integration/tests/check-runtime-capture.py`：使用隔离副本中的场景和视频，验证独立高质量任务、1080p 输出、原生背景和缩略图更新；PID/FPS 不变、帧数继续增长。
- 管理 UI 测试额外检查按钮仅在当前动态壁纸可用，以及取消确认不发送覆盖请求。

集成结果保存在 `reports/hq-recapture/`。测试使用自备的场景与视频素材，不改实际桌面或原始图库。

## 许可证收集检查

`make check-licenses` 验证运行包的声明复制、引用的通用许可全文、未知私有库与缺失声明的拒绝路径、
Wayland 生成代码声明。测试仅使用临时合成文件，不访问图库或修改桌面。它也包含在 `make check` 中。
许可全文的收集不替代对应源码交付及发布前的实际构建审查。

## 完整包验收

`make check` 包含路径、资源事务和原子安装单元测试。
`python3 packaging/check-minimal-loader.py <完整 ZIP>` 验证私有库与声明的宿主 ABI 闭包。
`python3 packaging/check-desktop.py <完整 ZIP>` 在独立 XDG/DBus/GNOME 中安装候选包，隐藏源码与旧 runtime，将程序目录绑定为只读，验证静态应用列表、管理界面、动态、工作区与 HQ 截图。
该图形测试需要本机自备 runtime 资源和已安装的兼容性测试扩展；通过 `WALLPAPER_TEST_RUNTIME` 指定私有资源目录，默认选择其中一张已有静态图的场景，也可设置 `WALLPAPER_TEST_ID`。加 `--video` 改用自动生成的合成视频，公共 assets 仍由用户自备。测试不修改真实桌面设置。

旧集成脚本需要显式设置 `WALLPAPER_TEST_SCENE_A`、`WALLPAPER_TEST_SCENE_B`、`WALLPAPER_TEST_SCENE_C` 和 `WALLPAPER_TEST_REFERENCE`，分别填写自己测试库中的条目 ID；不再内置真实素材 ID。旧脚本保留历史 runtime 布局约定，完整包验收使用上述新入口。
