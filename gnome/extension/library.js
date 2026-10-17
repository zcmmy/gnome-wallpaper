import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';

export function imageInfo(path) {
    try { const [format, width, height] = GdkPixbuf.Pixbuf.get_file_info(path);
        return format && width > 0 && height > 0 ? {width, height} : null;
    } catch (_) {return null;}
}
export function scenePath(root, id) {
    if (!GLib.path_is_absolute(root) || !id || id === '.' || id === '..' || /[\\/]/.test(id)) return null;
    return GLib.build_filenamev([root, id]);
}
export function readLibrary(root) {
    if (!root || !GLib.path_is_absolute(root)) return [];
    const directory = Gio.File.new_for_path(root);
    const entries = [];
    const files = directory.enumerate_children('standard::name,standard::type', Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
    try {
        let info;
        while ((info = files.next_file(null))) {
            if (info.get_file_type() !== Gio.FileType.DIRECTORY) continue;
            const id = info.get_name(), path = scenePath(root, id);
            if (!path) continue;
            try {
                const project = Gio.File.new_for_path(path + '/project.json');
                if (project.query_info('standard::size', 0, null).get_size() > 1048576) continue;
                const [, bytes] = project.load_contents(null);
                const data = JSON.parse(new TextDecoder().decode(bytes));
                const type = String(data.type ?? '').toLowerCase();
                let note = {};
                try {const [, raw] = Gio.File.new_for_path(path + '/.wallpaper-adapter.json').load_contents(null); note = JSON.parse(new TextDecoder().decode(raw));} catch (_) {}
                const still = path + '/static-background.png';
                const preview = typeof data.preview === 'string' && !/[\\/]/.test(data.preview) ? path + '/' + data.preview : null;
                entries.push({id, path, title:String(data.title || id), type, still,
                    thumbnail:path + '/thumbnail.jpg', preview, ready:!!imageInfo(still),
                    warning:typeof note.renderWarning === 'string' ? note.renderWarning : '', supported:['scene','video'].includes(type)});
            } catch (_) { /* A partial download is not a library entry. */ }
        }
    } finally {files.close(null);}
    return entries.sort((a,b) => a.id.localeCompare(b.id, undefined, {numeric:true}));
}
export function writeThumbnail(path) {
    const pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path + '/static-background.png', 480, 270, true);
    const tmp = path + '/.thumbnail-' + GLib.uuid_string_random() + '.jpg';
    pixbuf.savev(tmp, 'jpeg', ['quality'], ['85']);
    Gio.File.new_for_path(tmp).move(Gio.File.new_for_path(path + '/thumbnail.jpg'), Gio.FileCopyFlags.OVERWRITE, null, null);
}
// Called only by an explicit image-picker action in the preferences process.
export function replaceStaticImage(path, source) {
    const pixbuf = GdkPixbuf.Pixbuf.new_from_file(source);
    const tmp = path + '/.static-' + GLib.uuid_string_random() + '.png';
    const dest = Gio.File.new_for_path(path + '/static-background.png');
    try {
        pixbuf.apply_embedded_orientation().savev(tmp, 'png', [], []);
        Gio.File.new_for_path(tmp).move(dest, Gio.FileCopyFlags.OVERWRITE, null, null);
        writeThumbnail(path);
    } finally {try {Gio.File.new_for_path(tmp).delete(null);} catch (_) {}}
}
