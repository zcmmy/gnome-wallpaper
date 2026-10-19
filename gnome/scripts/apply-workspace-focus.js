// Replace only the focus callback; no extension reload or renderer restart.
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {restoreWorkspaceFocus} from '../extension/windowFocus.js';
export function apply() {
    const ext = Main.extensionManager.lookup('wallpaperengine@waylandwe')?.stateObj;
    if (!ext?._manager || ext._destroyed)
        throw new Error('请先启用壁纸管理扩展');
    Object.getPrototypeOf(ext)._refocusNormalWindow = restoreWorkspaceFocus;
    // No immediate focus manipulation: the next focus event uses the new logic.
    ext._workspaceFocusRevision = 1;
    return '工作区焦点修复已加载；播放进程、壁纸、帧率和通知设置未改变。';
}
