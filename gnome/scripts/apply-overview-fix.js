// Explicit, current-session-only update for a Shell that has cached revision 8.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
const ROOT = Gio.File.new_for_uri(import.meta.url).get_parent().get_parent().get_parent().get_path();
const {OverviewWallpaper} = await import(Gio.File.new_for_path(ROOT + '/runtime/live-extension/wallpaperengine@waylandwe/overviewWallpaper.js').get_uri());
let exported = null;
export function apply() {
    const ext = Main.extensionManager.lookup('wallpaperengine@waylandwe')?.stateObj;
    if (!ext?._rendererActor) throw new Error('Start the desktop wallpaper trial first.');
    if (!ext._overviewWallpaper) {
        const bridge = new OverviewWallpaper(ext);
        ext._overviewWallpaper = bridge;
        const adopt = ext._tryAdoptWindow;
        const forget = ext._forgetWindow;
        const disable = ext.disable;
        ext._tryAdoptWindow = function (...args) {
            const result = adopt.apply(this, args);
            this._overviewWallpaper?.refresh();
            return result;
        };
        ext._forgetWindow = function (...args) {
            this._overviewWallpaper?.clearSurface();
            return forget.apply(this, args);
        };
        ext.disable = function (...args) {
            this._overviewWallpaper?.destroy();
            this._overviewWallpaper = null;
            this._tryAdoptWindow = adopt;
            this._forgetWindow = forget;
            this.disable = disable;
            exported?.unexport();
            exported = null;
            return disable.apply(this, args);
        };
        bridge.refresh();
    }
    if (!exported) {
        exported = Gio.DBusExportedObject.wrapJSObject(`<node><interface name="org.wallpaper.Adapter.Overview">
            <method name="Snapshot"><arg type="s" direction="out"/></method>
            </interface></node>`, {Snapshot() {return JSON.stringify(snapshot());}});
        exported.export(Gio.DBus.session, '/org/gnome/Shell/WallpaperAdapterOverview');
    }
    snapshot();
    return 'Overview wallpaper fix applied for this session; panel and Dock settings unchanged.';
}
export function snapshot() {
    const ext = Main.extensionManager.lookup('wallpaperengine@waylandwe')?.stateObj;
    const result = {time:new Date().toISOString(), overview:Main.overview.visible,
        rendererPid:ext?._proc?.get_identifier(), rendering:ext?._overviewWallpaper?.snapshot()};
    GLib.file_set_contents(ROOT + '/reports/live-overview-status.json', JSON.stringify(result,null,2));
    return result;
}
