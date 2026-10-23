// Explicit Looking Glass entry. Reload only this extension; never restart Shell.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
const UUID='wallpaperengine@waylandwe';
function read(path) {
    const [,bytes]=Gio.File.new_for_path(path).load_contents(null);
    return JSON.parse(new TextDecoder().decode(bytes));
}
export async function apply() {
    const prepared=read(GLib.get_user_state_dir()+'/gnome-wallpaper/session-package.json');
    const record=Main.extensionManager.lookup(UUID);
    if(!record?.stateObj?._manager)throw new Error('请先启用当前壁纸扩展');
    const old=record.stateObj;
    if(old._fullPackageSession===prepared.identity)return '完整包已在当前会话生效。';
    if(old._proc||old._manager.capture||old._manager.runtimeCapture?.job)throw new Error('请先关闭动态并等待截图结束，再应用更新。');
    if(record.path!==prepared.installed)throw new Error('准备目录与实际安装目录不符');
    const file=Gio.File.new_for_path(record.path+'/package-manifest.json');
    const [,bytes]=file.load_contents(null);
    if(GLib.compute_checksum_for_bytes(GLib.ChecksumType.SHA256,new GLib.Bytes(bytes)).slice(0,16)!==prepared.identity)
        throw new Error('插件包已更新，请重新准备会话入口');
    const metadata=read(record.path+'/metadata.json');
    const module=await import(Gio.File.new_for_path(prepared.module).get_uri());
    const replacement=new module.default({...metadata,dir:record.dir,path:record.path});
    const previousMetadata=record.metadata;
    const saved={};for(const key of ['library-root','assets-path','wallpaperengine-path','engine'])saved[key]=old._settings.get_string(key);
    await Main.extensionManager._callExtensionDisable(UUID);
    try {
        record.metadata=metadata;record.stateObj=replacement;
        await Main.extensionManager._callExtensionEnable(UUID);
        if(record.state!==1||!replacement._manager)throw new Error(record.error||'完整包未能启用');
        replacement._fullPackageSession=prepared.identity;
        Gio.Settings.sync();
        return '完整包已加载，保持静态模式；可以打开壁纸管理器进行桌面测试。';
    } catch(error) {
        try {replacement.disable();} catch(_) {}
        const settings=replacement.getSettings();
        for(const [key,value] of Object.entries(saved))settings.set_string(key,value);
        record.metadata=previousMetadata;record.stateObj=old;
        Main.extensionManager._changeExtensionState(record,2);
        await Main.extensionManager._callExtensionEnable(UUID);
        throw error;
    }
}
