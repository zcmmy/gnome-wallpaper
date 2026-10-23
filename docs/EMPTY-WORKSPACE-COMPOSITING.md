# 空工作区与 Shell 合成

## 症状与判断依据

用户报告：动态壁纸在没有普通应用窗口的工作区遮蔽顶栏和 Dock，已有应用窗口时正常。
此前 Forge 修复处理的是普通窗口被平铺和置顶的问题，不覆盖本次合成路径。

隔离会话检查显示：空工作区的壁纸是 DESKTOP 类型、不置顶，顶栏与 Dock actor 仍可见，
监视器也没有被标记为全屏。单纯抬高顶栏或修改 Forge 规则缺少依据。

[Mutter 48.7 原生合成代码](https://github.com/GNOME/mutter/blob/48.7/src/compositor/meta-compositor-view-native.c)
的 find_scanout_candidate 会检查顶部窗口的绘制范围是否覆盖显示器、surface 是否被遮挡等条件，
不要求窗口带有 fullscreen 状态。无普通应用窗口时，覆盖显示器的壁纸可能成为直接扫描输出候选，
其缓冲区直接送往显示设备，绕过包含 Shell 界面的完整合成结果。

这是与用户症状和源码相符的原因判断。headless 测试没有物理 KMS CRTC，不能直接复现硬件扫描输出，
因此自动测试不能单独证明硬件桌面效果。2026-10-19，用户执行会话更新后已确认：
空工作区的顶栏和 Dock 显示正常。修复已完成真实桌面验收。

## 实现

- 新增 compositingGuard 模块，在所属渲染窗口创建、首帧映射之前持有一个 Mutter unredirect 抑制引用。
- GNOME 48 使用 global.compositor.disable_unredirect / enable_unredirect；兼容旧 Meta display 接口。
  仅选择其中一种成对接口，不能重复持有两份引用。
- 重复窗口事件或重复会话更新不增加引用；清理窗口时释放一次。
- 异常退出、停止播放和插件停用都经窗口清理释放；清理操作抛错时也通过 finally 释放。
- 尊重其他扩展持有的引用，不通过全局计数重置或停用其他扩展解决问题。
- 静态模式不持有本插件的引用，不新增定时器、后台渲染器或持续截图。

该接口作用于合成器：动态壁纸存在期间，其他窗口的直接扫描输出也被抑制。
它不更改真正全屏应用的 Shell 隐藏行为，不改变壁纸 FPS、分辨率、效果、顶栏和 Dock 设置，
但相对直接输出可能增加合成成本，不能声称 GPU 开销必然不变。

## 验证

```bash
bash gnome/tests/check.sh
python3 integration/tests/check-empty-workspace.py fixed
python3 integration/tests/check-empty-workspace.py hot-update
```

测试需要 GNOME、已构建的独立运行包、Forge、Blur my Shell、Dash to Dock、Rounded Windows 和自备场景素材。
WALLPAPER_TEST_RUNTIME 指定运行目录，WALLPAPER_TEST_ID 可选择用户自己的测试项；
未指定时从运行包中选择已有静态图的场景。全部设置与扩展开关在独立 XDG/DBus/headless 会话中操作。

覆盖静态无引用、空工作区动态启动、打开/关闭最后一个应用、工作区切换、概览返回、
真正的全屏应用进入/退出、动态重启、异常退出及插件停用。
测试保存 Shell 可见性、全屏状态、保护引用和截图，并核对真实桌面 dconf 未改变。
旧 v0.0.1 在缺少保护引用的断言处失败；这是对代码保护条件的验证，不是物理扫描输出的复现。

热更新测试先加载 v0.0.1，动态播放后连续执行两次更新，确认进程身份与 FPS 不变、引用不累积。
单位测试另覆盖其他引用持有者、旧 API、获取失败、重复释放和不支持接口的处理。

## 当前会话部署

用原子安装器更新插件及运行包；把 compositingGuard.js 放入 runtime/compositing-fix-live/。
在 Looking Glass 中显式执行：

```javascript
(await import('file://<项目目录>/gnome/scripts/apply-compositing-fix.js')).apply()
```

该入口只加载不含 GObject 注册的保护模块，并包装窗口创建/清理方法；可以保护当前正在播放的窗口，
无需停止动态或重启 Shell。静态状态执行不会主动开启播放。
执行后在真实空工作区检查顶栏与 Dock，并检查关闭最后一个应用后能否正常显示。
