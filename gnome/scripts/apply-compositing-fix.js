// Update only composition ownership; no module reload, mode change or restart.
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {holdCompositing, releaseCompositing} from '../../runtime/compositing-fix-live/compositingGuard.js';
export function apply() {
    const ext = Main.extensionManager.lookup('wallpaperengine@waylandwe')?.stateObj;
    if (!ext?._manager || ext._destroyed) throw new Error('请先启用壁纸管理扩展');
    const prototype = Object.getPrototypeOf(ext);
    if (!prototype._compositingFixInstalled) {
        const created = prototype._onWindowCreated, forget = prototype._forgetWindow;
        prototype._onWindowCreated = function (window) {
            if (!this._destroyed && this._proc !== null && this._rendererWindow === null && this._windowMatchesRenderer(window))
                holdCompositing(this);
            return created.call(this, window);
        };
        prototype._forgetWindow = function (...args) {
            try { return forget.apply(this, args); }
            finally { releaseCompositing(this); }
        };
        prototype._compositingFixInstalled = true;
    }
    // Also protect a renderer that is already mapped or still starting.
    if (ext._proc && !ext._procStopping) holdCompositing(ext);
    return '空工作区合成保护已加载；播放、壁纸、帧率和桌面配置未改变。请切换到空工作区检查顶栏与 Dock。';
}
