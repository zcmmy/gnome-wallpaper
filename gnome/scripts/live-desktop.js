import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import Meta from 'gi://Meta';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const ROOT = Gio.File.new_for_uri(import.meta.url).get_parent().get_parent().get_parent().get_path();
const UUID = 'wallpaperengine@waylandwe';
const OUT = ROOT + '/runtime/live-desktop';
let exported = null;
let dockModule = null;
let baseline = null;
let timers = new Set();

function actorInfo(actor) {
    if (!actor) return null;
    const info = {x: actor.x, y: actor.y, width: actor.width, height: actor.height,
        visible: actor.visible, opacity: actor.opacity, scale: [actor.scale_x, actor.scale_y],
        effects: (actor.get_effects?.() ?? []).map(e => e.get_name?.() ?? String(e))};
    if (actor instanceof St.Widget) {
        const node = actor.get_theme_node();
        info.style = actor.get_style();
        info.styleClass = actor.get_style_class_name();
        info.background = node.get_background_color().to_string();
        info.foreground = node.get_foreground_color().to_string();
        info.font = node.get_font().to_string();
        info.borders = [St.Side.TOP, St.Side.RIGHT, St.Side.BOTTOM, St.Side.LEFT].map(s => ({
            width: node.get_border_width(s), color: node.get_border_color(s).to_string()}));
    }
    return info;
}
function chromeInfo() {
    const dock = dockModule?.dockManager?.mainDock;
    return {panel: actorInfo(Main.panel), panelBox: actorInfo(Main.layoutManager.panelBox),
        dock: actorInfo(dock), dash: actorInfo(dock?.dash), dashBackground: actorInfo(dock?.dash?._background)};
}
export function snapshot() {
    const ext = Main.extensionManager.lookup(UUID)?.stateObj;
    const w = ext?._rendererWindow;
    const actor = ext?._rendererActor;
    const layer = ext?._rendererLayer;
    const frame = w?.get_frame_rect();
    const chrome = chromeInfo();
    const states = Object.fromEntries(Main.extensionManager.getUuids().map(id => {
        const e = Main.extensionManager.lookup(id);
        return [id, {state: e.state, error: e.error}];
    }));
    const result = {time: new Date().toISOString(), chrome, chromeUnchanged: JSON.stringify(chrome) === JSON.stringify(baseline),
        persistentEnabledExtensions: global.settings.get_strv('enabled-extensions'), extensions: states,
        renderer: {pid: ext?._proc?.get_identifier() ?? null, socket: ext?._socketPath ?? null,
            adopted: Boolean(w), skipTaskbar: w?.skip_taskbar, fullscreen: w?.is_fullscreen(),
            focused: Boolean(w) && global.display.focus_window === w,
            inAltTab: w ? global.display.get_tab_list(Meta.TabList.NORMAL_ALL, null).filter(v => !v.skip_taskbar).includes(w) : false,
            frame: frame ? {x:frame.x,y:frame.y,width:frame.width,height:frame.height} : null,
            paintOrigin: layer && actor ? [layer.x+actor.x+actor.translation_x,layer.y+actor.y+actor.translation_y] : null,
            actor: actorInfo(actor), children: actor?.get_children().map(actorInfo),
            parentIsBackground: layer?.get_parent() === Main.layoutManager._backgroundGroup},
        terminal: global.get_window_actors().filter(a => /terminal/i.test(a.meta_window.get_wm_class() ?? '')).map(a => ({
            app: a.meta_window.get_wm_class(), actor:actorInfo(a), children:a.get_children().map(actorInfo)}))};
    GLib.file_set_contents(OUT + '/status.json', JSON.stringify(result, null, 2));
    return result;
}
export async function stop() {
    for (const id of timers) GLib.source_remove(id);
    timers.clear();
    await Main.extensionManager._callExtensionDisable(UUID);
    exported?.unexport();
    exported = null;
    GLib.file_set_contents(OUT + '/stopped.txt', new Date().toISOString());
    return 'Trial stopped; original static wallpaper remains configured.';
}
export async function start() {
    if (exported) return 'Trial is already active.';
    GLib.mkdir_with_parents(OUT, 0o700);
    // Read the existing Dock instance; do not re-enable or reconfigure it.
    const dock = Main.extensionManager.lookup('dash-to-dock@micxgx.gmail.com');
    if (dock) dockModule = await import(dock.dir.get_child('extension.js').get_uri());
    baseline = chromeInfo();
    GLib.file_set_contents(OUT + '/chrome-before.json', JSON.stringify(baseline, null, 2));
    let ext = Main.extensionManager.lookup(UUID);
    if (!ext) ext = Main.extensionManager.createExtensionObject(UUID,
        Gio.File.new_for_path(ROOT + '/runtime/live-extension/' + UUID), 2);
    await Main.extensionManager.loadExtension(ext);
    // Runtime activation only. Deliberately do not call enableExtension(),
    // which persists the UUID to the next-login enabled-extensions list.
    await Main.extensionManager._callExtensionEnable(UUID);
    if (ext.state !== 1) throw new Error('Extension did not become active: ' + ext.error);
    const xml = `<node><interface name="org.wallpaper.Adapter.Trial">
        <method name="Snapshot"><arg type="s" direction="out"/></method>
        <method name="Stop"><arg type="s" direction="out"/></method>
        </interface></node>`;
    exported = Gio.DBusExportedObject.wrapJSObject(xml, {
        Snapshot() {return JSON.stringify(snapshot());},
        StopAsync(_params, invocation) {
            stop().then(result => invocation.return_value(new GLib.Variant('(s)', [result])))
                .catch(e => invocation.return_dbus_error('org.wallpaper.Adapter.Error', e.message));
        },
    });
    exported.export(Gio.DBus.session, '/org/gnome/Shell/WallpaperAdapterTrial');
    for (const seconds of [2, 10, 30, 60]) {
        const id = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, seconds, () => {
            timers.delete(id);
            try {snapshot();} catch (e) {console.error('Wallpaper trial snapshot: ' + e.stack);}
            return GLib.SOURCE_REMOVE;
        });
        timers.add(id);
    }
    return 'Wallpaper trial started for this Shell session only; no autostart entry added.';
}
