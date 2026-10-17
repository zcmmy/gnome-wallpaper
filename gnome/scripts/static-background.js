// Run with gjs -m; does not load GNOME Shell or start the renderer.
import Gio from 'gi://Gio';
import {applyStaticWallpaper, restoreStaticWallpaper} from '../extension/staticWallpaper.js';
if (ARGV[0] === '--restore') {
    if (!restoreStaticWallpaper()) throw new Error('No backup or settings not writable');
} else {
    if (!ARGV[0] || !applyStaticWallpaper(ARGV[0], ARGV[1] ?? 'fill'))
        throw new Error('Pass a scene directory containing static-background.png');
}
Gio.Settings.sync();
print('Static wallpaper settings updated.');
