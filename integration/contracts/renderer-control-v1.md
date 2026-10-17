# GNOME ↔ portghost 当前集成契约（对应 renderer status.api = 1）

## 边界

GNOME 端不链接渲染器库、不读取 C++ 内部对象；渲染器不调用 Shell API 或 GSettings。
这是一份现有行为的文档，不新增版本协商，也不代表兼容全部 Wallpaper Engine 资源。
其他桌面可通过相同的窗口与指针接口替代 GNOME 适配层。

## 启动与画面

调用配置的可执行程序，参数为：

```text
--window 0x0xWIDTHxHEIGHT --fps 15 --listen --no-fullscreen-pause
--scaling fill --silent --assets-dir ASSETS WALLPAPER
```

WIDTH/HEIGHT 是合成器逻辑尺寸；GLFW framebuffer 随缩放得到实际像素尺寸。
--silent 只静音壁纸自身声音；系统音频频谱处理单独存在。
GNOME 用 Meta.WaylandClient.new/spawnv 提供 WAYLAND_SOCKET 并追踪 owns_window。
渲染器输出一个普通无装饰 Wayland surface；桌面嵌入、Alt-Tab 排除、概览副本均由 GNOME 端负责。
现有窗口模式使用 GLFW。其他后端不保证实现 pointer 命令。

## 控制通道

GNOME 创建私有临时目录，将其中 socket 路径用 LWE_SOCKET 环境变量传给渲染器。
AF_UNIX 流套接字，每行一个 UTF-8 JSON 请求/响应；请求 id 为整数。
请求：{"id":1,"cmd":"status","args":{}}
成功：{"id":1,"ok":true,"status":"done","result":{...}}
失败：{"id":1,"ok":false,"error":"..."}
诊断工具使用 status、pause、resume、set-fps 等现有命令；完整命令集合以 C++ CommandDispatcher 为准。
画面不经过此通道，禁止把帧缓冲/大图像当作指针消息发送。

## 指针请求

{"id":2,"cmd":"pointer","args":{"x":0.5,"y":0.5,"left":false,"right":false,"active":true}}
x/y 为目标屏幕内的归一化坐标 [0,1]，左上角为 (0,0)。按钮/active 为布尔值。
GNOME 每50ms最多发一条，并且最多一个请求未完成；套接字操作异步，不能阻塞 Shell。
当前实现连接有1秒超时；无回复时不会堆积额外请求，不保证连接成功后的每次读都有硬超时。
点击普通应用、顶栏、Dock 不转发；概览/锁屏时 active=false。
渲染器超过500ms未更新时使外部输入失效并释放按钮。点击、帧计数等可通过 status.pointer/status.frames 检查。

## 生命周期

SIGTERM 正常停止；有界等待后强制终止；暂停/恢复的进程信号由适配层管理。
屏幕关闭逻辑保留现有行为，本次未新增可见性优化策略。
源码目录重组不改变命令字段、发送频率或绘制行为。

## 高质量静态图辅助任务

仅缺图且用户显式开启动态时，由 captureWorker.py 启动独立短时进程。
日常桌面渲染器不附带 screenshot 参数，也不升高分辨率。
截图任务使用私有 GNOME Wayland 会话，输出窗口为 1920×1080：

```text
--screenshot TEMP.png --screenshot-delay 45 --screenshot-hq --texturedetail full
--fps 15 --silent --disable-mouse --disable-parallax --no-audioreactive --no-fullscreen-pause
```

--screenshot-hq 仅在同时存在 --screenshot 时提升 scene FBO 及相关合成目标，
覆盖 3840×2160 可见区域，保留原始布局/相机坐标，最终按覆盖面积平均缩小。
视频读取实际解码帧尺寸，不先插值放大到 4K；TEXB0004 原始数据哨兵兼容仍保留。
辅助任务只在完全解码验证成功后原子输出 PNG，并回收渲染器与私有合成器。
插件仅在 static-background.png 不存在时移入，更新缩略图和原生背景；用户替换优先。
关闭动态、换图、禁用、超时均取消任务。任务本身用用户级锁串行，不常驻。

## 显式运行时截图

请求：`{"id":1,"cmd":"screenshot","args":{"path":"/绝对路径/私有临时目录/frame.png"}}`。
仅接受已有目录下尚不存在的 `.png` 输出路径；单进程一次最多处理一个截图。
渲染线程读取最近完成的当前帧，保持播放尺寸、FPS、动画、频谱与指针设置不变；工作线程编码 PNG。
成功应答 `result.queued=true` 只代表已读取并排队编码，不代表文件已经保存。
文件经 `.tmp` 编码完成后原子 rename 成目标路径；等待方必须验证 PNG 内容，并设置超时。
此命令不属于持久状态变更，不启动高质量截图 worker。

管理器使用私有输出目录和文件监听，无常驻截图轮询；30 秒超时。
用户通过 JSON `manager-command` 发送 `action=capture-static`、目标 `id`、唯一 `request`。
完成时再次核对当前壁纸、进程和模式，并按原图 etag 条件原子替换；新图片优先。
取消会移除私有目录，阻止迟到的 PNG 编码结果重新落盘；不会停止播放进程。
`runtime-status.runtimeCaptureSupported` 表示管理器支持该操作；`runtimeCapture` 包含请求标识和结果。
