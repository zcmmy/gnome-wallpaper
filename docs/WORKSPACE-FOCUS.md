# 工作区切换与“应用已就绪”通知

## 原因

动态壁纸使用一个受插件管理的 Wayland 桌面窗口。工作区切换或点击空桌面时，
Mutter 仍可能将输入焦点交给该窗口。旧版 `_refocusNormalWindow()` 使用
`get_tab_list(Meta.TabList.NORMAL, null)` 查询所有工作区，并对第一个应用调用 `activate()`。
这可能选中另一个工作区的应用。

GNOME 48 的隔离回归已记录这一链路：当前工作区为 1，壁纸获得焦点，
回调时间戳为 0，工作区 0 的测试应用收到 `window-demands-attention`。
Shell 据此创建“应用已就绪”通知。提示中的应用不是重新启动了；它是被壁纸插件错误请求激活。

[Mutter 48.7 的窗口激活实现](https://github.com/GNOME/mutter/blob/48.7/src/core/window.c)
在零时间戳跨工作区激活时设置 demands-attention；非零时间戳则还可能引发工作区切换。
因此仅消除通知、改变时间戳或按壁纸标题屏蔽通知，都不能修正焦点归还行为。

## 修复

`gnome/extension/windowFocus.js` 集中处理壁纸焦点：

- 只有焦点确实落在当前壁纸窗口上时才介入；映射窗口时不干扰已有应用焦点。
- 查询范围限于活动工作区，排除壁纸、隐藏或最小化窗口及不参与任务切换的窗口。
- 通过 `focus()` 归还输入焦点，不调用具有激活、抬高、恢复最小化及跨工作区语义的 `activate()`。
- 当前工作区没有合适应用时释放输入焦点，不请求其他工作区的应用。

不修改 GNOME 通知处理器、Forge 设置、顶栏、Dock、播放帧率或 C++ 渲染管线。
正常应用的注意请求与通知保持原行为。模块不新增定时器、全局包装或常驻任务。

## 验证

```bash
bash gnome/tests/check.sh
python3 integration/tests/check-workspace-focus.py baseline
python3 integration/tests/check-workspace-focus.py fixed
python3 integration/tests/check-workspace-focus.py hot-update
```

隔离集成测试使用独立 DBus、XDG 配置和 headless GNOME Wayland 会话，
复制当前用户已安装的 Forge、Blur my Shell、Dash to Dock 和圆角扩展用于兼容验证。
通过 `WALLPAPER_TEST_RUNTIME` 指定自备运行包；默认使用仓库同级的 `wallpaper-runtime`。
测试从自备图库选择具备静态图的场景，也可用 `WALLPAPER_TEST_ID` 指定本地目录标识。
测试不提交资源，结束后核对真实 GNOME 设置没有变化。

基线默认取 `dev` 的扩展源码；当修复以后合并到 dev，应设置
`FOCUS_BASELINE_REF=5408d17` 继续复现修复前行为。基线预期产生注意请求；
修复和热更新预期没有工作区切换引发的请求，且普通应用主动请求注意时仍有通知。
另覆盖可见应用焦点、空工作区、最小化窗口、概览返回、顶栏与 Dock、动态停止和重启。
结果保存在本机 `reports/workspace-focus/`，不纳入 Git。

验证环境为 GNOME 48 / Wayland；真实触控板手势仍需用户在当前桌面验收。

## 部署与当前会话

正式代码修订为 15。通过 `gnome/scripts/install-extension.py` 原子替换已安装扩展及
运行包内扩展，保留旧目录供回退；下次会话加载新代码，仍遵循显式开启动态的规则。

GNOME 缓存当前会话的模块，因此磁盘安装不会立即替换已运行方法。
`gnome/scripts/apply-workspace-focus.js` 提供一次性的 Looking Glass 更新：
仅将壁纸插件的焦点方法替换为同一修复实现，重复执行不会叠加包装，不停止渲染器。
该入口不立即调整当前焦点，也不清除已存在的普通应用通知。
