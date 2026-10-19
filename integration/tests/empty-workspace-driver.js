import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
const delay=ms=>new Promise(r=>GLib.timeout_add(0,ms,()=>{r();return false;}));
function assert(value,message){if(!value)throw new Error(message);}
export async function startTest(ext) {
    const out=GLib.getenv('TEST_OUT'),testCase=GLib.getenv('TEST_CASE'),states=[];
    let app=null;
    const snapshot=async (label,{active=true,fullscreen=false}={})=>{
        const panel=Main.layoutManager.panelBox;
        const docks=Main.uiGroup.get_children().filter(a=>a.name==='dashtodockContainer');
        const state={label,ready:ext._rendererReady,guard:!!ext._compositingRelease,
            fullscreen:global.display.get_monitor_in_fullscreen(0),panelVisible:panel.visible,panelMapped:panel.mapped,
            dock:docks.map(a=>({visible:a.visible,mapped:a.mapped})),workspace:global.workspace_manager.get_active_workspace_index()};
        assert(state.guard===active,'Unbalanced composition ownership: '+JSON.stringify(state));
        assert(state.fullscreen===fullscreen,'Unexpected fullscreen detection: '+JSON.stringify(state));
        if(!fullscreen){assert(state.panelVisible&&state.panelMapped,'Panel hidden: '+label);assert(docks.length&&docks.every(a=>a.visible&&a.mapped),'Dock hidden: '+label);}
        if(active)assert(state.ready,'Renderer not ready: '+label);
        states.push(state);console.warn('EMPTY-STATE '+JSON.stringify(state));
        const stream=Gio.File.new_for_path(out+'/'+label+'.png').replace(null,false,0,null);
        await new Shell.Screenshot().screenshot(false,stream);stream.close(null);
    };
    const start=async()=>{ext._settings.set_boolean('enabled',true);for(let i=0;i<100&&!ext._rendererReady;i++)await delay(150);await delay(700);assert(ext._rendererReady,'Renderer failed to start');};
    try {
        await delay(2500);Main.overview.hide();await delay(700);await snapshot('static-empty',{active:false});
        await start();
        if(testCase==='hot-update'){
            const proc=ext._proc,fps=ext._settings.get_int('fps');
            const update=await import('./applyCompositingTest.js');update.apply();update.apply();
            assert(ext._proc===proc&&ext._settings.get_int('fps')===fps,'Hot update changed playback');
        }
        await snapshot('dynamic-empty');
        const launcher=new Gio.SubprocessLauncher({flags:0});launcher.setenv('WAYLAND_DISPLAY','forge-test',true);
        app=launcher.spawnv(['python3',GLib.getenv('TEST_PROFILE')+'/app.py']);await delay(1600);
        await snapshot('with-application');
        const first=global.workspace_manager.get_active_workspace();
        if(global.workspace_manager.n_workspaces<2)global.workspace_manager.append_new_workspace(false,global.get_current_time());
        global.workspace_manager.get_workspace_by_index(1).activate(global.get_current_time());await delay(1100);
        await snapshot('switched-empty');
        Main.overview.show();await delay(700);Main.overview.hide();await delay(700);await snapshot('overview-return');
        first.activate(global.get_current_time());await delay(700);
        app.send_signal(10);await delay(1200);await snapshot('real-fullscreen',{fullscreen:true});
        app.send_signal(12);await delay(900);await snapshot('fullscreen-exit');
        app.force_exit();app=null;await delay(1000);await snapshot('last-application-closed');
        ext._settings.set_boolean('enabled',false);await delay(1200);await snapshot('static-restored',{active:false});
        await start();await snapshot('restarted-empty');
        ext._proc.force_exit();await delay(1200);await snapshot('renderer-exited',{active:false});
        ext._settings.set_boolean('enabled',false);await delay(300);
        await start();
        Main.extensionManager.disableExtension('wallpaperengine@waylandwe');await delay(1000);
        await snapshot('extension-disabled',{active:false});
        GLib.file_set_contents(out+'/summary.json',JSON.stringify(states,null,2));console.warn('EMPTY-TEST PASS');
    } catch(e) {console.error('EMPTY-TEST ERROR '+e.message+' '+e.stack);}
    finally {app?.force_exit();ext._settings?.set_boolean('enabled',false);await delay(500);global.context.terminate();}
}
