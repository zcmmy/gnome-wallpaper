// Explicit session update: no Shell restart, mode change or renderer launch.
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import WallpaperExtension from '../../runtime/forge-fix-live/wallpaperExtension.js';
export function apply() {
    const ext = Main.extensionManager.lookup('wallpaperengine@waylandwe')?.stateObj;
    if (!ext?._manager) throw new Error('请先启用壁纸管理扩展');
    if (ext._proc || ext._procStopping || ext._settings.get_boolean('enabled'))
        throw new Error('请先关闭动态模式，等待渲染器退出后再执行');
    if (ext._manager.capture || ext._manager.runtimeCapture?.job)
        throw new Error('请等待截图任务结束后再执行');
    const prototype = Object.getPrototypeOf(ext);
    for (const key of ['_protectFromTiling', '_restoreTilingFilter', '_onWindowCreated', '_tryAdoptWindow', '_startEngine'])
        Object.defineProperty(prototype, key, Object.getOwnPropertyDescriptor(WallpaperExtension.prototype, key));
    if (!prototype._forgeFixInstalled) {
        const disable = prototype.disable;
        prototype.disable = function (...args) {
            this._restoreTilingFilter();
            return disable.apply(this, args);
        };
        prototype._forgeFixInstalled = true;
    }
    return 'Forge 兼容修复已加载；可在管理器中开启动态模式测试。壁纸、帧率、顶栏和 Dock 设置未改变。';
}
