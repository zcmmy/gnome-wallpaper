from pathlib import Path
import shutil
r=Path(__file__).resolve().parents[2];d=r/'runtime/manager-ui-test/data/gnome-shell/extensions/wallpaperengine@waylandwe'
shutil.copytree(r/'gnome/extension',d,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git'))

(d/'uiShellDriver.js').write_text('''import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
export function startUiTest(ext){
 const root=GLib.getenv('WALLPAPER_TEST_ROOT');
 const exported=Gio.DBusExportedObject.wrapJSObject(`<node><interface name="org.wallpaper.UiTest"><method name="Capture"><arg type="s" direction="in"/><arg type="s" direction="out"/></method></interface></node>`,{CaptureAsync:async([name],inv)=>{try{const path=root+'/reports/manager/'+name+'.png';const stream=Gio.File.new_for_path(path).replace(null,false,0,null);await new Shell.Screenshot().screenshot(false,stream);stream.close(null);inv.return_value(new GLib.Variant('(s)',[path]));}catch(e){inv.return_dbus_error('org.wallpaper.Error',e.message);}}});
 exported.export(Gio.DBus.session,'/org/gnome/Shell/WallpaperUiTest');
 GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT,4,()=>{Main.overview.hide();const launcher=new Gio.SubprocessLauncher({flags:Gio.SubprocessFlags.NONE});launcher.setenv('WAYLAND_DISPLAY','wallpaper-manager-ui-test',true);launcher.setenv('GDK_BACKEND','wayland',true);launcher.set_stdout_file_path(root+'/reports/manager/ui.log');launcher.set_stderr_file_path(root+'/reports/manager/ui-error.log');const proc=launcher.spawnv(['gjs','-m',root+'/integration/tests/manager-ui-driver.js']);proc.wait_async(null,()=>{ext._settings.set_boolean('enabled',false);GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT,3,()=>{exported.unexport();global.context.terminate();return GLib.SOURCE_REMOVE;});});return GLib.SOURCE_REMOVE;});
}
''')
p=d/'wallpaperExtension.js';s=p.read_text()+"\nimport {startUiTest} from './uiShellDriver.js';\n";s=s.replace('        this._manager.start();','        this._manager.start();\n        startUiTest(this);');p.write_text(s)
s=(r/'integration/tests/manager-session.sh.in').read_text().replace('manager-test','manager-ui-test').replace('runtime/manager-ui-test/wallpapers','wallpapers').replace('1280x720','1440x1000');s=s.replace('gsettings set "$s" wallpaperengine-path "$WALLPAPER_TEST_ROOT/renderer/scripts/run.sh"','gsettings set "$s" wallpaperengine-path "$WALLPAPER_TEST_ROOT/renderer/scripts/run.sh"');(r/'runtime/manager-ui-test/run-test.sh').write_text(s)
