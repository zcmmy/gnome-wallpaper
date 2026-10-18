import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
const delay=ms=>new Promise(r=>GLib.timeout_add(0,ms,()=>{r();return false;}));
export async function startTest(ext){
 const out=GLib.getenv('TEST_OUT'),baseline=GLib.getenv('TEST_CASE')==='baseline';let app;const snapshots=[];
 const snap=label=>{
  const w=ext._rendererWindow,a=ext._rendererActor,bg=Main.layoutManager._backgroundGroup;
  const forge=Main.extensionManager.lookup('forge@jmmaranan.com')?.stateObj?.extWm;
  const state={label,ready:ext._rendererReady,type:w?.get_window_type(),above:w?.is_above(),title:w?.get_title(),frame:w?Object.fromEntries(['x','y','width','height'].map(k=>[k,w.get_frame_rect()[k]])):null,tracked:!!(w&&forge?.tree?.findNode(w)),parent:a?String(a.get_parent()):null,inLayer:a?.get_parent()===ext._rendererLayer,backgroundIndex:global.window_group.get_children().indexOf(bg),children:global.window_group.get_children().map(c=>({name:c.name,type:String(c),title:c.get_meta_window?.()?.get_title()}))};
  const appWindow=global.get_window_actors().map(a=>a.get_meta_window()).find(w=>w.get_title()==='Forge regression app');
  state.appTracked=!!(appWindow&&forge?.tree?.findNode(appWindow));
  state.appAboveBackground=!!(appWindow&&global.window_group.get_children().indexOf(appWindow.get_compositor_private())>state.backgroundIndex);
  if(state.ready&&!baseline){
   if(state.type!==Meta.WindowType.DESKTOP||state.above||state.tracked||!state.inLayer||!state.appAboveBackground)throw new Error('Wallpaper isolation failed: '+JSON.stringify(state));
  }
  snapshots.push(state);console.warn('FORGE-TEST '+JSON.stringify(state));return state;
 };
 try{
  if(GLib.getenv('TEST_CASE')==='hot-update')(await import('./applyForgeTest.js')).apply();
  await delay(2000);Main.overview.hide();await delay(500);
  const launcher=new Gio.SubprocessLauncher({flags:Gio.SubprocessFlags.NONE});launcher.setenv('WAYLAND_DISPLAY','forge-test',true);app=launcher.spawnv(['python3',GLib.getenv('TEST_PROFILE')+'/app.py']);
  await delay(1500);snap('static');
  ext._settings.set_boolean('enabled',true);
  for(let i=0;i<100&&!ext._rendererReady;i++)await delay(150);
  await delay(2500);if(!ext._rendererReady)throw new Error('Renderer not ready');snap('dynamic');
  if(!baseline){Main.extensionManager.enableExtension('forge@jmmaranan.com');await delay(800);snap('forge-enabled');
   Main.extensionManager.disableExtension('forge@jmmaranan.com');await delay(800);snap('forge-disabled');
   Main.extensionManager.enableExtension('forge@jmmaranan.com');await delay(800);const state=snap('forge-reenabled');if(!state.appTracked)throw new Error('Forge stopped managing applications');}
  const file=Gio.File.new_for_path(out+'/desktop.png'),stream=file.replace(null,false,0,null);await new Shell.Screenshot().screenshot(false,stream);stream.close(null);
  const application=global.get_window_actors().map(a=>a.get_meta_window()).find(w=>w.get_title()==='Forge regression app');
  if(!application)throw new Error('Test application missing');
  application.activate(global.get_current_time());await delay(1200);snap('app-focused');
  ext._settings.set_boolean('enabled',false);await delay(1600);snap('stopped');
  if(!baseline){ext._settings.set_boolean('enabled',true);for(let i=0;i<100&&!ext._rendererReady;i++)await delay(150);await delay(500);if(!ext._rendererReady)throw new Error('Restart failed');snap('restarted');ext._settings.set_boolean('enabled',false);await delay(1000);}
  GLib.file_set_contents(out+'/summary.json',JSON.stringify(snapshots,null,2));console.warn('FORGE-TEST PASS');
 }catch(e){console.error('FORGE-TEST ERROR '+e.message+' '+e.stack);}
 finally{app?.force_exit();ext._settings.set_boolean('enabled',false);await delay(800);global.context.terminate();}
}
