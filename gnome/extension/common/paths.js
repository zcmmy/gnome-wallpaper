import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
export const DATA_VERSION = 1;
export const BACKEND_PROTOCOL = 1;
export const extensionRoot = Gio.File.new_for_uri(import.meta.url).get_parent().get_parent().get_path();
export const paths = {
    data: GLib.build_filenamev([GLib.get_user_data_dir(), 'gnome-wallpaper']),
    cache: GLib.build_filenamev([GLib.get_user_cache_dir(), 'gnome-wallpaper']),
    state: GLib.build_filenamev([GLib.get_user_state_dir(), 'gnome-wallpaper']),
    backend: extensionRoot + '/backend/linux-x86_64',
};
paths.library = paths.data + '/wallpapers';
paths.assets = paths.data + '/assets';
paths.renderer = paths.backend + '/bin/renderer';
export function readJson(path) {
    const [, bytes] = Gio.File.new_for_path(path).load_contents(null);
    return JSON.parse(new TextDecoder().decode(bytes));
}
export function writeJson(path, value) {
    Gio.File.new_for_path(path).replace_contents(new TextEncoder().encode(JSON.stringify(value, null, 2)+'\n'), null, false, Gio.FileCreateFlags.PRIVATE, null);
}
export function initializePaths(settings) {
    for (const path of [paths.data, paths.library, paths.cache, paths.state]) GLib.mkdir_with_parents(path, 0o700);
    const index = paths.data + '/library.json';
    if (Gio.File.new_for_path(index).query_exists(null) && readJson(index).version !== DATA_VERSION)
        throw new Error('图库数据版本不受支持；未修改数据，请使用匹配版本或恢复备份。');
    const oldRoot = settings.get_string('library-root');
    const legacy = paths.state + '/legacy-settings.json';
    if (oldRoot && oldRoot !== paths.library && !Gio.File.new_for_path(legacy).query_exists(null)) {
        const saved = {};
        for (const key of ['library-root','assets-path','wallpaperengine-path','selected-id','rotation-state']) saved[key] = settings.get_string(key);
        saved['rotation-ids'] = settings.get_strv('rotation-ids');
        saved['rotation-enabled'] = settings.get_boolean('rotation-enabled');
        saved.fps = settings.get_int('fps');
        writeJson(legacy, saved);
    }
    // These keys remain for reading old installations, never as user-configurable program paths.
    for (const [key,value] of [['library-root',paths.library],['assets-path',paths.assets],['wallpaperengine-path',paths.renderer],['engine','wallpaperengine']])
        if (settings.get_string(key) !== value) settings.set_string(key, value);
    const oldBackup = GLib.build_filenamev([GLib.get_user_state_dir(),'wallpaper-adapter','original-background.json']);
    const backup = paths.state + '/original-background.json';
    if (!Gio.File.new_for_path(backup).query_exists(null) && Gio.File.new_for_path(oldBackup).query_exists(null))
        Gio.File.new_for_path(oldBackup).copy(Gio.File.new_for_path(backup), Gio.FileCopyFlags.NONE, null, null);
    return paths;
}
export function backendStatus() {
    try {
        const manifest = readJson(paths.backend + '/manifest.json');
        if (manifest.format !== 1 || manifest.protocol !== BACKEND_PROTOCOL || !manifest.capabilities?.includes('capture-hq'))
            throw new Error('内置后端版本或截图协议不匹配');
        if (!GLib.file_test(paths.renderer, GLib.FileTest.IS_EXECUTABLE)) throw new Error('内置后端不完整，请重新安装完整发行包');
        return {ready:true, version:manifest.version, protocol:manifest.protocol};
    } catch(e) {return {ready:false,error:'内置后端不可用：'+e.message};}
}
export function assetsReady() {
    return ['models','shaders','scripts'].every(name=>GLib.file_test(paths.assets+'/'+name,GLib.FileTest.IS_DIR));
}
export function privateRuntimeDirectory() {
    const base = GLib.get_user_runtime_dir();
    if (base && GLib.file_test(base,GLib.FileTest.IS_DIR)) {
        const dir=Gio.File.new_for_path(base+'/gnome-wallpaper-'+GLib.uuid_string_random());
        dir.make_directory(null);dir.set_attribute_uint32('unix::mode',0o700,Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,null);
        return dir.get_path();
    }
    return GLib.dir_make_tmp('gnome-wallpaper-XXXXXX');
}
export function thumbnailPath(scene) {
    const dir=paths.cache+'/thumbnails';GLib.mkdir_with_parents(dir,0o700);
    return dir+'/'+GLib.compute_checksum_for_string(GLib.ChecksumType.SHA256,scene,-1)+'.jpg';
}
