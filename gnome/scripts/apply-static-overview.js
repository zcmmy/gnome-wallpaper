// Update only this session's overview integration, without reloading Shell.
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {StaticOverview} from '../../runtime/static-overview-live/staticOverview.js';
import {WallpaperManager} from '../../runtime/static-overview-live/manager.js';
export function apply() {
    const ext = Main.extensionManager.lookup('wallpaperengine@waylandwe')?.stateObj;
    if (!ext?._manager) throw new Error('请先启用壁纸管理扩展');
    const engine = Object.getPrototypeOf(ext);
    if (!engine._staticOverviewHook) {
        const enable = engine.enable, disable = engine.disable, stop = engine._stopEngine;
        engine.enable = function (...args) {
            const result = enable.apply(this, args);
            this._staticOverview ??= new StaticOverview(this);
            this._manager?.publish();
            return result;
        };
        engine.disable = function (...args) {
            this._staticOverview?.destroy(); this._staticOverview = null;
            return disable.apply(this, args);
        };
        engine._stopEngine = function (...args) {
            const result = stop.apply(this, args);
            this._staticOverview?.sync();
            return result;
        };
        engine._staticOverviewHook = true;
    }
    Object.getPrototypeOf(ext._manager).publish = WallpaperManager.prototype.publish;
    ext._staticOverview ??= new StaticOverview(ext);
    ext._manager.publish();
    return '静态应用列表背景已启用；不启动渲染器，不修改外观或帧率设置。';
}
