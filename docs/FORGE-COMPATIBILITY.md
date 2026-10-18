# Forge 平铺兼容修复

## 问题与责任边界

验证环境：GNOME 48.7 / Wayland，Forge 扩展 version 89。
[Forge](https://github.com/forge-ext/forge) 不是壁纸渲染器：它在 Shell 中维护窗口平铺树，
通过 Mutter 调整应用窗口的位置、大小、焦点与堆叠，再添加边框等 Shell actor。
C++ 渲染器生成画面，GNOME/Mutter 负责最后的桌面合成。

原实现把渲染 actor 移进背景组，却没有把 Meta.Window 从 NORMAL 改为 DESKTOP。
Forge 的 `lib/extension/window.js::trackWindow/_validWindow` 接受普通窗口，
`lib/extension/tree.js::Node.float` 在 `float-always-on-top-enabled` 开启时调用 `make_above()`。
本机该选项已开启。因此“背景组中的 actor”和“Forge 管理的置顶应用窗口”同时存在，
两套窗口管理逻辑发生冲突。浮动白名单不会解决它，因为浮动窗口仍可能置顶。

隔离会话已复现 NORMAL、Forge tree 有对应节点、above=true 以及 Mutter 堆叠断言。
仅在延迟接管时调用 make_desktop 仍留下 Forge 节点，不能解决创建事件顺序问题。
隔离测试中应用最终仍可见，未稳定复现用户会话的持续遮挡。
2026-10-19，用户在真实桌面执行会话更新并开启动态模式后确认“应用窗口显示正常”。
该修复已纳入 v0.0.1；修复分支 fix/forge-wallpaper-stacking 保留。

空工作区遮蔽顶栏和 Dock 的后续问题见 [Shell 合成说明](EMPTY-WORKSPACE-COMPOSITING.md)。

## 修复

- 渲染进程启动前，仅为当前 Forge 管理器包装 `_validWindow`。
  使用 `Meta.WaylandClient.owns_window` 排除本插件拥有的窗口，不用 PID、标题或 app-id 猜测。
  Forge 的新窗口回调已绑定，直接替换 `trackWindow` 无法拦截已有绑定，因此包装其动态查询的方法。
- 在收到所属窗口创建事件时同步调用 `make_desktop`，不等待 actor 接管计时器。
  后启用/重启的平铺管理器可直接依据 DESKTOP 类型跳过它。
- 接管时清除可能残留的 above 状态，继续使用原有背景组与鼠标桥。
- 插件停用时恢复包装；再次启动时识别新的 Forge 实例。
  如果另一个扩展后来包装了同一方法，则停用自己的过滤而不覆盖对方的方法。

不修改 Forge 文件、浮动规则、设置、顶栏、Dock、C++ 渲染器、帧率或开机启动。
过滤依赖 Forge 89 的内部 `_validWindow` 接口；后续 Forge 更新需重新验证。

## 验证

```bash
bash gnome/tests/check.sh
python3 integration/tests/check-forge.py fixed
python3 integration/tests/check-forge.py late-forge
python3 integration/tests/check-forge.py baseline
python3 integration/tests/check-forge.py hot-update
```

集成测试需要本机已安装 Forge、Blur my Shell、Dash to Dock 和 Rounded Windows，
以及默认位于相邻 wallpaper-runtime 的独立运行包和自备场景素材。
测试脚本保留本机开发素材的定位约定，运行前需按自己的素材调整测试配置。
可用 `WALLPAPER_TEST_RUNTIME` 指定运行包，用 `FORGE_BASELINE_REF` 指定对照提交。
测试复制这些扩展和配置到独立 XDG/DBus/headless Shell，仅操作隔离会话。
前后比对真实桌面 dconf，输出位于忽略的 reports/forge/。

断言覆盖：DESKTOP 类型、不置顶、不进入 Forge tree、背景组层级、普通应用仍被平铺管理、
Forge 后启用和反复开关、动态停止/重启。另有归属过滤、同 PID 非所属窗口、包装恢复的单元测试。

## 当前会话更新

安装器更新磁盘文件后，当前 Shell 仍可能缓存旧模块。开发时把完整插件复制到
runtime/forge-fix-live（使用 gnome/scripts/stage-forge-update.py，避免重复注册 GType），
再在 Looking Glass 显式执行：

```javascript
(await import('file:///home/clx/workspace/wallpaper_adapter/gnome/scripts/apply-forge-fix.js')).apply()
```

迁移要求静态模式且没有截图任务，只替换窗口管理方法，不启动渲染器、不重启 Shell。
之后手动开启动态模式，检查平铺、切换应用和工作区。
