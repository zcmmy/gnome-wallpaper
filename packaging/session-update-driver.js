import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
const delay=ms=>new Promise(r=>GLib.timeout_add(0,ms,()=>{r();return false;}));
const assert=(v,m)=>{if(!v)throw new Error(m);};
function run(argv) {
    const launch=new Gio.SubprocessLauncher({flags:Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE});
    launch.setenv('WAYLAND_DISPLAY','package-session-test',true);
    const proc=launch.spawnv(argv);
    return new Promise((resolve,reject)=>proc.communicate_utf8_async(null,null,(p,result)=>{
        try {const [,out,error]=p.communicate_utf8_finish(result);if(!p.get_successful())throw new Error(error||out);resolve(out);}catch(e){reject(e);}
    }));
}
export async function runSessionTest(old) {
    try {
        await delay(2000);Main.overview.hide();
        const source=GLib.getenv('TEST_SOURCE');
        assert(!old._proc,'Old extension is playing');
        assert(!JSON.parse(old._settings.get_string('runtime-status')).packageProtocol,'Not an old cached module');
        await run(['/usr/bin/python3',source+'/packaging/install.py',GLib.getenv('TEST_ARCHIVE'),'--yes','--destination',old.path]);
        await run(['/usr/bin/python3',source+'/gnome/scripts/stage-package-session.py',old.path,GLib.get_user_state_dir()+'/gnome-wallpaper']);
        const entry=await import(Gio.File.new_for_path(source+'/gnome/scripts/apply-full-package.js').get_uri());
        await entry.apply();
        const next=Main.extensionManager.lookup('wallpaperengine@waylandwe').stateObj;
        assert(next!==old&&next._manager,'Old instance retained');
        assert(JSON.parse(next._settings.get_string('runtime-status')).packageProtocol===1,'New protocol absent');
        assert(!next._proc&&next._settings.get_int('fps')===15,'Update changed playback');
        await entry.apply();assert(Main.extensionManager.lookup('wallpaperengine@waylandwe').stateObj===next,'Repeated apply replaced instance');
        next._settings.set_boolean('enabled',true);
        for(let i=0;i<100&&!next._rendererReady;i++)await delay(150);
        assert(next._rendererReady,'New renderer not ready');
        assert(next._rendererLayer.get_parent()===Main.layoutManager._backgroundGroup,'Wrong desktop layer');
        next._settings.set_boolean('enabled',false);await delay(1000);
        assert(!next._proc&&!next._pointerBridge,'Static teardown failed');
        console.warn('SESSION-UPDATE PASS');
    } catch(e) {console.error('SESSION-UPDATE ERROR '+e.message+' '+e.stack);}
    finally {await Main.extensionManager._callExtensionDisable('wallpaperengine@waylandwe');global.context.terminate();}
}
