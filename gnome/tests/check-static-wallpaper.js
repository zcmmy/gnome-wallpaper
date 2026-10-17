import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {applyStaticWallpaper, restoreStaticWallpaper} from '../extension/staticWallpaper.js';
function assert(value, message) {if (!value) throw new Error(message);}
const settings = new Gio.Settings({schema_id:'org.gnome.desktop.background'});
settings.set_string('picture-uri', 'file:///original-light.jpg');
settings.set_string('picture-uri-dark', 'file:///original-dark.jpg');
settings.set_string('picture-options', 'centered');
const original = () => settings.get_string('picture-uri') === 'file:///original-light.jpg' &&
    settings.get_string('picture-uri-dark') === 'file:///original-dark.jpg' && settings.get_string('picture-options') === 'centered';
assert(!applyStaticWallpaper('/nonexistent') && original(), 'missing image changes settings');
assert(!applyStaticWallpaper('12345') && original(), 'unresolved ID changes settings');
const scene = ARGV[0];
assert(applyStaticWallpaper(scene, 'fill'), 'apply failed');
const uri = Gio.File.new_for_path(scene + '/static-background.png').get_uri();
assert(settings.get_string('picture-uri') === uri && settings.get_string('picture-uri-dark') === uri, 'both modes must use prepared still');
assert(settings.get_string('picture-options') === 'zoom', 'fill scaling mismatch');
assert(applyStaticWallpaper(scene, 'fill'), 'idempotent apply failed');
assert(applyStaticWallpaper(scene, 'fit') && settings.get_string('picture-options') === 'scaled', 'fit mismatch');
assert(applyStaticWallpaper(scene, 'stretch') && settings.get_string('picture-options') === 'stretched', 'stretch mismatch');
const invalid = GLib.build_filenamev([GLib.get_user_state_dir(), 'invalid-scene']);
GLib.mkdir_with_parents(invalid, 0o700);
GLib.file_set_contents(invalid + '/static-background.png', 'invalid png');
assert(!applyStaticWallpaper(invalid) && settings.get_string('picture-uri') === uri, 'invalid still changes settings');
assert(restoreStaticWallpaper() && original(), 'original backup overwritten on repeated activation');
print('PASS: static image application, dark/light modes, scaling, missing/invalid image, repeated startup and original restoration');
