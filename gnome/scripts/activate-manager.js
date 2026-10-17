// Explicit current-session reload. Never modifies the enabled-extensions list.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
const UUID='wallpaperengine@waylandwe';
export async function apply() {
    const record=Main.extensionManager.lookup(UUID);
    if (!record) throw new Error('当前会话尚未发现壁纸扩展，请重新登录后再启用。');
    if (!record.stateObj) {
        await Main.extensionManager._callExtensionEnable(UUID);
        if (record.state!==1 || !record.stateObj?._manager) throw new Error(record.error || '新版扩展未启动');
        return '壁纸管理已启用：静态模式，不添加登录启动项。';
    }
    if (record.stateObj._manager) return '新版壁纸管理已在运行。';
    const old=record.stateObj;
    // Use the exact existing module directory: GJS caches its GObject classes.
    const module=await import(record.dir.get_child('wallpaperExtension.js').get_uri());
    const replacement=new module.default({...record.metadata,dir:record.dir,path:record.path});
    const settings=replacement.getSettings();
    if (!settings.settings_schema.has_key('library-root')) throw new Error('请先更新扩展 schemas。');
    await Main.extensionManager._callExtensionDisable(UUID);
    try {
        record.stateObj=replacement;
        await Main.extensionManager._callExtensionEnable(UUID);
        if (record.state!==1 || !replacement._manager) throw new Error(record.error || '新版扩展未启动');
        Gio.Settings.sync();
        return '壁纸管理已启用：静态模式，不启动渲染器，不添加登录启动项。';
    } catch (e) {
        try {replacement.disable();} catch (_) {}
        record.stateObj=old;
        Main.extensionManager._changeExtensionState(record,2);
        await Main.extensionManager._callExtensionEnable(UUID);
        throw e;
    }
}
