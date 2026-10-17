// Private nested Shell only; hold transitions midway to inspect native stills.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
export function startTest(ext) {
    ext._settings.set_boolean('enabled', true);
    let tick = 0, pid = null;
    const settings = new Gio.Settings({schema_id:'org.gnome.desktop.background'});
    const expected = Gio.File.new_for_path(ext._resolveScenePath() + '/static-background.png').get_uri();
    const assert = (value, why) => {if (!value) throw new Error(why);};
    const check = label => {
        assert(settings.get_string('picture-uri') === expected && settings.get_string('picture-uri-dark') === expected, 'wrong native wallpaper');
        console.warn('STATIC-TEST ' + JSON.stringify({label, pid:ext._proc?.get_identifier(),
            adopted:!!ext._rendererActor, uri:settings.get_string('picture-uri'),
            fps:ext._settings.get_int('fps'), transition:!!Main.wm._workspaceAnimation._switchData}));
    };
    const capture = async label => {
        const path = GLib.getenv('WALLPAPER_TEST_ROOT') + '/reports/static-background/' + label + '.png';
        const stream = Gio.File.new_for_path(path).replace(null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
        try {await new Shell.Screenshot().screenshot(false, stream);}
        catch(e) {console.error('STATIC-TEST ERROR ' + e.stack);}
        finally {stream.close(null);}
    };
    const controller = Main.wm._workspaceAnimation;
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1000, () => {
        try {
            tick++;
            if (tick === 5) {Main.overview.hide(); pid=ext._proc?.get_identifier(); assert(ext._rendererActor, 'renderer not adopted'); check('started');}
            if (tick === 8) {
                controller._prepareWorkspaceSwitch([0, 1]);
                for (const group of controller._switchData.monitors) group.progress = .5;
            }
            if (tick === 10) {check('mid-transition'); capture('mid-transition'); assert(ext._proc.get_identifier() === pid, 'renderer restarted during swipe');}
            if (tick === 12) controller._finishWorkspaceSwitch(controller._switchData);
            if (tick === 14) {
                controller._prepareWorkspaceSwitch([0, 1]);
                for (const group of controller._switchData.monitors) group.progress = .8;
            }
            if (tick === 15) {check('repeat-transition'); capture('repeat-transition');}
            if (tick === 16) controller._finishWorkspaceSwitch(controller._switchData);
            if (tick === 18) ext._settings.set_boolean('enabled', false);
            if (tick === 21) {check('stopped-static'); assert(!ext._rendererActor, 'renderer still present'); capture('stopped-static');}
            if (tick === 22) ext._settings.set_boolean('enabled', true);
            if (tick === 27) {check('restarted'); assert(ext._rendererActor && ext._proc.get_identifier() !== pid, 'restart failed'); assert(!ext._buildWallpaperEngineArgv().includes('--screenshot'), 'runtime captures image');}
            if (tick === 28) ext._settings.set_boolean('enabled', false);
            if (tick === 31) {check('complete'); global.context.terminate(); return GLib.SOURCE_REMOVE;}
        } catch (e) {console.error('STATIC-TEST ERROR ' + e.stack); global.context.terminate(); return GLib.SOURCE_REMOVE;}
        return GLib.SOURCE_CONTINUE;
    });
}
