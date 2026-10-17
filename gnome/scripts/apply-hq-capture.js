// Current-session patch only; no Shell restart, schema writes or autostart changes.
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {WallpaperManager} from '../../runtime/hq-live/manager.js';
export function apply() {
    const record = Main.extensionManager.lookup('wallpaperengine@waylandwe');
    const ext = record?.stateObj;
    if (!ext?._manager) throw new Error('请先启用壁纸管理扩展');
    const manager = ext._manager;
    manager.cancelCapture();
    const prototype = Object.getPrototypeOf(manager);
    for (const name of ['startCapture','prepareCapture','cancelCapture','adopted','publish'])
        prototype[name] = WallpaperManager.prototype[name];
    const engine = Object.getPrototypeOf(ext);
    if (!engine._hqCaptureHook) {
        const original = engine._buildWallpaperEngineArgv;
        engine._buildWallpaperEngineArgv = function () {
            // Loaded old code used prepareCapture while constructing playback args.
            const prepare = this._manager?.prepareCapture;
            if (this._manager) this._manager.prepareCapture = () => null;
            try {return original.call(this);}
            finally {if (this._manager) this._manager.prepareCapture = prepare;}
        };
        engine._hqCaptureHook = true;
    }
    if (ext._rendererReady) manager.startCapture(ext._resolveScenePath());
    manager.publish();
    return '4K → 1080p 高质量截图已启用；日常播放设置保持原样。';
}
