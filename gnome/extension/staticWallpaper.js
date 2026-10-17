// Prepared image only: never capture a frame or start another renderer here.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';

const KEYS = ['picture-uri', 'picture-uri-dark', 'picture-options'];
const backupPath = () => GLib.build_filenamev([
    GLib.get_user_state_dir(), 'wallpaper-adapter', 'original-background.json']);

export function applyStaticWallpaper(scene, scaling = 'fill') {
    if (!scene || !GLib.path_is_absolute(scene)) return false;
    const image = Gio.File.new_for_path(GLib.build_filenamev([scene, 'static-background.png']));
    if (!image.query_exists(null)) return false;
    const [format, width, height] = GdkPixbuf.Pixbuf.get_file_info(image.get_path());
    if (!format || width <= 0 || height <= 0) {
        console.warn('Wallpaper static background is not a valid image: ' + image.get_path());
        return false;
    }
    const settings = new Gio.Settings({schema_id:'org.gnome.desktop.background'});
    if (KEYS.some(key => !settings.is_writable(key))) return false;
    const uri = image.get_uri();
    const options = {fill:'zoom', fit:'scaled', stretch:'stretched'}[scaling] ?? 'zoom';
    if (settings.get_string('picture-uri') === uri &&
        settings.get_string('picture-uri-dark') === uri &&
        settings.get_string('picture-options') === options) return true;

    const backup = Gio.File.new_for_path(backupPath());
    GLib.mkdir_with_parents(backup.get_parent().get_path(), 0o700);
    if (!backup.query_exists(null)) {
        const original = Object.fromEntries(KEYS.map(key => [key, settings.get_string(key)]));
        // Exclusive creation preserves the original configuration across restarts.
        const stream = backup.create(Gio.FileCreateFlags.PRIVATE, null);
        try {stream.write_all(new TextEncoder().encode(JSON.stringify(original, null, 2)), null);}
        finally {stream.close(null);}
    }
    settings.delay();
    settings.set_string('picture-uri', uri);
    settings.set_string('picture-uri-dark', uri);
    settings.set_string('picture-options', options);
    settings.apply();
    return true;
}

// Explicit restoration only: disabling playback deliberately keeps the still.
export function restoreStaticWallpaper() {
    const backup = Gio.File.new_for_path(backupPath());
    if (!backup.query_exists(null)) return false;
    const [, bytes] = backup.load_contents(null);
    const original = JSON.parse(new TextDecoder().decode(bytes));
    if (KEYS.some(key => typeof original[key] !== 'string'))
        throw new Error('Invalid original-background.json');
    const settings = new Gio.Settings({schema_id:'org.gnome.desktop.background'});
    if (KEYS.some(key => !settings.is_writable(key))) return false;
    settings.delay();
    for (const key of KEYS) settings.set_string(key, original[key]);
    settings.apply();
    return true;
}
