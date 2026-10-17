import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import Clutter from 'gi://Clutter';
import Meta from 'gi://Meta';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// Loaded only into the temporary nested Shell, never installed on the desktop.
export function startTest(ext) {
    ext._settings.set_boolean('enabled', true);
    const capture = async label => {
        const path = GLib.getenv('WALLPAPER_TEST_ROOT') + '/reports/overview-' + label + '.png';
        const stream = Gio.File.new_for_path(path).replace(null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        try {await new Shell.Screenshot().screenshot(false, stream);}
        catch(e) {console.error('WALLPAPER-TEST ERROR capture ' + e.stack);}
        finally {stream.close(null);}
    };
    let tick = 0;
    let initialPid = null;
    const pointer = Clutter.get_default_backend().get_default_seat()
        .create_virtual_device(Clutter.InputDeviceType.POINTER_DEVICE);
    const snapshot = label => {
        const w = ext._rendererWindow;
        console.warn('WALLPAPER-TEST ' + JSON.stringify({label, pid: ext._proc?.get_identifier(),
            overviewWallpaper:ext._overviewWallpaper?.snapshot() ?? {backdrop:null,clones:[]}, socket: ext._socketPath, adopted: Boolean(w), skipTaskbar: w?.skip_taskbar,
            sticky: w?.is_on_all_workspaces(), rect: w ? {x:w.get_frame_rect().x, y:w.get_frame_rect().y, width:w.get_frame_rect().width, height:w.get_frame_rect().height} : null,
            inTabList: w ? global.display.get_tab_list(Meta.TabList.NORMAL_ALL, null).filter(w => !w.skip_taskbar).includes(w) : null,
            paintOrigin: ext._rendererActor ? [ext._rendererLayer.x + ext._rendererActor.x + ext._rendererActor.translation_x, ext._rendererLayer.y + ext._rendererActor.y + ext._rendererActor.translation_y] : null,
            monitor: ext._targetGeometry(),
            parentIsBackground: ext._rendererLayer?.get_parent() === Main.layoutManager._backgroundGroup,
            focused: Boolean(w) && global.display.focus_window === w, visible: ext._rendererActor?.visible,
            shellPointer: global.get_pointer(), overview: Main.overview.visible, overviewState:Main.overview._overview._controls._stateAdjustment.value,
            restartChangedPid: initialPid !== ext._proc?.get_identifier()}));
    };
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, () => {
        try {
            tick++;
            if (tick === 5) {Main.overview.hide(); initialPid = ext._proc?.get_identifier(); snapshot('mapped');}
            const geo = ext._targetGeometry();
            if ([8, 14, 20].includes(tick)) {
                const fraction = tick === 8 ? .1 : tick === 14 ? .9 : .5;
                pointer.notify_absolute_motion(GLib.get_monotonic_time(), geo.x + geo.width * fraction, geo.y + geo.height * fraction);
            }
            if ([10, 16, 22].includes(tick)) snapshot('pointer-' + tick);
            if (tick === 24) Main.overview.show();
            if (tick === 26) {snapshot('overview'); capture('windows');}
            if (tick === 27) Main.overview.dash.showAppsButton.checked = true;
            if (tick === 29) {snapshot('apps'); capture('apps');}
            if (tick === 30) Main.overview.hide();
            if (tick === 31) global.workspace_manager.get_workspace_by_index(1)?.activate(global.get_current_time());
            if (tick === 32) {snapshot('workspace'); ext._setPaused(true);}
            if (tick === 33) {snapshot('paused'); ext._setPaused(false);}
            if (tick === 34) {
                const [, log] = GLib.file_get_contents(GLib.get_user_state_dir() + '/wallpaper-adapter/renderer.log');
                GLib.file_set_contents(GLib.getenv('WALLPAPER_TEST_ROOT') + '/reports/gnome-renderer-first.log', log);
                ext._settings.set_int('fps', 20);
                ext._settings.set_string('scaling', ext._settings.get_string('scaling') === 'fit' ? 'fill' : 'fit');
            }
            if (tick === 40) snapshot('restarted');
            if (tick === 42) ext._settings.set_boolean('enabled', false);
            if (tick === 46) {snapshot('disabled'); ext._settings.set_boolean('enabled', true);}
            if (tick === 52) snapshot('reenabled');
            if (tick === 54) {ext._settings.set_boolean('enabled', false);}
            if (tick === 58) {snapshot('complete'); global.context.terminate(); return GLib.SOURCE_REMOVE;}
        } catch (e) {console.error('WALLPAPER-TEST ERROR ' + e.stack); global.context.terminate(); return GLib.SOURCE_REMOVE;}
        return GLib.SOURCE_CONTINUE;
    });
}
