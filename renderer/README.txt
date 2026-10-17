C++ 渲染层

source/ 是修改后的 portghost 源码快照，由顶层 Git 管理。职责：读取 WE 场景/资源、音频 FFT、脚本/动画/特效、OpenGL 绘制、通用窗口和输入接口。
它不读取 GNOME 扩展源码或 GSettings，不导入 GNOME Shell；Meta.WaylandClient 提供的 WAYLAND_SOCKET 是标准 Wayland 连接环境。
原仓库支持的其他桌面/视频/web 功能继续保留，本次没有抽取或删除引擎内部子系统。

构建：scripts/build.sh；运行任意参数：scripts/run.sh ARGS；独立预览：scripts/preview.sh。
测试：tests/check.sh。构建不进入 gnome/，测试不使用 GJS。
图像输出通过 Wayland 窗口；控制输入通过 integration/contracts/ 记录的 CLI 和 Unix socket。
运行资源由调用者传入 --assets-dir 和壁纸路径，源码不包含用户壁纸。

静态截图：仅在 takeScreenshot 的保存线程中进行重采样。缩小按源像素覆盖面积平均，放大采用像素中心双线性插值；保持现有裁切、方向和 RGB 色彩处理。动态帧渲染不经过该滤镜。
测试：tests/check-capture.cpp 覆盖缩放、裁切、翻转、边缘钳制和高频棋盘格。integration/tests/check-capture-runtime.py 在隔离的 GNOME 会话中验证图库截图，不更改实际桌面。
诊断：仅调试时设置 LWE_SCREENSHOT_REFERENCE=1，可在截图旁生成原始 FBO PNG 和 UV/尺寸 JSON，用于从完全相同的一帧对比采样算法。正常运行不生成诊断文件。

高质量静态图：--screenshot PATH --screenshot-hq 仅供一次性截图进程使用；场景布局和相机坐标保持原值，场景 FBO 覆盖 3840×2160 可见区域（fill 模式按画布比例可能更高），低分辨率场景及其特效合成目标会同步提高采样密度。输出由窗口大小指定，默认 1920×1080，沿用面积缩小滤镜。无 --screenshot-hq 的普通播放分辨率和分配规则完全保留。视频直接读取实际解码帧，避免无意义的 4K 放大。
