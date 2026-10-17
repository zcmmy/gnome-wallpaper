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
make check-renderer 中视频纹理测试需要先 make renderer；优先使用 build/renderer，兼容旧 build/portghost。
图形集成和截图对照保留了开发图库的 ID/场景约定，需要自备匹配素材，不能当作无素材 CI。
check-static-overview 还需要本机装有 Blur my Shell 和 Dash to Dock；它们不是正式运行的强制依赖。

## 当前帧截图测试

- `make check`：命令路径校验、覆盖成功、原图并发修改保护、重复请求、取消及静态状态保护。
- `python3 integration/tests/check-runtime-capture.py`：使用隔离副本中的场景和视频，验证真实截图、原生背景和缩略图更新；PID/FPS 不变、帧数继续增长。
- 管理 UI 测试额外检查按钮仅在当前动态壁纸可用，以及取消确认不发送覆盖请求。

集成结果保存在 `reports/runtime-capture/`。测试使用自备的韶华和星极素材，不改实际桌面或原始图库。
