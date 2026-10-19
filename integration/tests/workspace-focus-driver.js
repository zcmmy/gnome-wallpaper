import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
const delay=ms=>new Promise(r=>GLib.timeout_add(0,ms,()=>{r();return false;}));
function assert(value,message){if(!value)throw new Error(message);}
export async function startTest(ext) {
    const testCase=GLib.getenv('TEST_CASE'), events=[], calls=[];
    const attention=global.display.connect('window-demands-attention',(_d,w)=>events.push({title:w.get_title(),workspace:w.get_workspace()?.index()}));
    const refocus=ext._refocusNormalWindow;
    if(testCase==='baseline')ext._refocusNormalWindow=function(w){calls.push({time:global.get_current_time(),focus:global.display.focus_window?.get_title(),workspace:global.workspace_manager.get_active_workspace_index()});return refocus.call(this,w);};
    let app=null;
    try {
        await delay(2500);Main.overview.hide();await delay(700);
        const launcher=new Gio.SubprocessLauncher({flags:0});launcher.setenv('WAYLAND_DISPLAY','focus-test',true);
        app=launcher.spawnv(['python3',GLib.getenv('TEST_PROFILE')+'/app.py']);
        let win;
        for(let i=0;i<100&&!win;i++){await delay(100);win=global.get_window_actors().map(a=>a.meta_window).find(w=>w.get_pid()===Number(app.get_identifier()));}
        assert(win,'Test app missing');await delay(500);
        const first=global.workspace_manager.get_active_workspace();
        ext._settings.set_boolean('enabled',true);
        for(let i=0;i<100&&!ext._rendererReady;i++)await delay(150);
        assert(ext._rendererReady,'Renderer missing');await delay(700);
        if(testCase==='hot-update'){
            const proc=ext._proc,fps=ext._settings.get_int('fps');
            const update=await import('./applyFocusTest.js');update.apply();update.apply();
            assert(ext._proc===proc&&ext._settings.get_int('fps')===fps,'Hot update changed playback');
        }
        events.length=0;calls.length=0;
        if(global.workspace_manager.n_workspaces<2)global.workspace_manager.append_new_workspace(false,global.get_current_time());
        const second=global.workspace_manager.get_workspace_by_index(1);
        for(let i=0;i<3;i++){
            second.activate(global.get_current_time());await delay(900);
            // Desktop focus can also be caused by a click while a workspace is empty.
            ext._rendererWindow.focus(global.get_current_time());await delay(350);
            assert(global.workspace_manager.get_active_workspace()===second,'Wallpaper switched back to application workspace');
            Main.overview.show();await delay(300);Main.overview.hide();await delay(350);
            assert(Main.layoutManager.panelBox.visible&&Main.layoutManager.panelBox.mapped,'Panel hidden on empty workspace');
            const docks=Main.uiGroup.get_children().filter(a=>a.name==='dashtodockContainer');
            assert(docks.length&&docks.every(a=>a.visible&&a.mapped),'Dock hidden on empty workspace');
            first.activate(global.get_current_time());await delay(650);
        }
        if(testCase!=='baseline'){
            win.focus(global.get_current_time());await delay(200);
            ext._refocusNormalWindow(ext._rendererWindow);
            assert(global.display.focus_window===win,'Unnecessary refocus disturbed app');
            ext._rendererWindow.focus(global.get_current_time());await delay(250);
            assert(global.display.focus_window===win,'Focus not returned to visible current app');
            win.minimize();await delay(250);
            ext._rendererWindow.focus(global.get_current_time());await delay(250);
            assert(win.minimized,'Wallpaper unminimized application');
            assert(global.display.focus_window!==ext._rendererWindow,'Empty workspace retained renderer focus');
            win.unminimize();await delay(250);
        }
        console.warn('FOCUS-DIAGNOSTIC '+JSON.stringify({events,calls}));
        if(testCase==='baseline')assert(events.length>0,'Baseline did not reproduce attention');
        else assert(events.length===0,'Workspace switch generated attention: '+JSON.stringify(events));
        const switchEvents=[...events];
        if(testCase!=='baseline'){
            second.activate(global.get_current_time());await delay(500);
            win.set_demands_attention();await delay(300);
            assert(events.length===1&&events[0].title===win.get_title(),'Ordinary application attention broken');
            assert(Main.messageTray.getSources().some(s=>s._window===win&&s.notifications.length>0),'Ordinary notification suppressed');
            const proc=ext._proc;
            ext._settings.set_boolean('enabled',false);await delay(1000);
            assert(ext._proc===null,'Static mode retained renderer');
            ext._settings.set_boolean('enabled',true);
            for(let i=0;i<100&&!ext._rendererReady;i++)await delay(150);
            assert(ext._rendererReady&&ext._proc!==proc,'Renderer restart failed');
            ext._rendererWindow.focus(global.get_current_time());await delay(200);
            assert(events.length===1,'Restart generated additional attention');
        }
        GLib.file_set_contents(GLib.getenv('TEST_OUT')+'/summary.json',JSON.stringify({switchEvents,events,calls},null,2));
        console.warn('FOCUS-TEST PASS');
    } catch(e) {console.error('FOCUS-TEST ERROR '+e.message+' '+e.stack);}
    finally {global.display.disconnect(attention);app?.force_exit();ext._settings?.set_boolean('enabled',false);await delay(500);global.context.terminate();}
}
