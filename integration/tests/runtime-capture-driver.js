import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GdkPixbuf from 'gi://GdkPixbuf';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {command} from './rendererClient.js';
const delay=ms=>new Promise(resolve=>GLib.timeout_add(GLib.PRIORITY_DEFAULT,ms,()=>{resolve();return GLib.SOURCE_REMOVE;}));
const assert=(v,m)=>{if(!v)throw new Error(m);};
const wait=async test=>{for(let i=0;i<2100;i++){if(test())return;await delay(100);}throw new Error('condition timeout');};
export async function startTest(ext) {
 const out=GLib.getenv('WALLPAPER_TEST_ROOT')+'/reports/hq-recapture/';const results=[];
 try {
  await delay(2000);Main.overview.hide();
  for(const id of [GLib.getenv('WALLPAPER_TEST_SCENE_A'),GLib.getenv('WALLPAPER_TEST_SCENE_C')]) {
   ext._settings.set_boolean('enabled',false);await wait(()=>!ext._proc);
   ext._settings.set_string('selected-id',id);ext._settings.set_boolean('enabled',true);
   await wait(()=>ext._rendererReady);await delay(1200);
   const before=await command(ext._socketPath,'status');const pid=ext._proc.get_identifier();
   ext._settings.set_string('manager-command',JSON.stringify({action:'capture-static',id,request:id+'-test'}));
   const workerPid=ext._manager.runtimeCapture.job?.worker?.get_identifier();
   assert(workerPid && workerPid!==pid,'independent capture worker not started');
   await delay(1000);const during=await command(ext._socketPath,'status');
   assert(during.frames>before.frames && ext._manager.runtimeCapture.job,'playback did not advance during capture');
   await wait(()=>ext._manager.runtimeCapture.result?.request===id+'-test' && ext._manager.runtimeCapture.result.state!=='capturing');
   assert(ext._manager.runtimeCapture.result.state==='done',JSON.stringify(ext._manager.runtimeCapture.result));
   assert(ext._proc.get_identifier()===pid && ext._rendererReady && ext._settings.get_boolean('enabled'),'capture restarted/stopped playback');
   const scene=ext._resolveScenePath(),pix=GdkPixbuf.Pixbuf.new_from_file(scene+'/static-background.png');
   assert(pix.get_width()===1920 && pix.get_height()===1080,'wrong HQ output size');
   assert(Gio.File.new_for_path(scene+'/thumbnail.jpg').query_exists(null),'missing thumbnail');
   const bg=new Gio.Settings({schema_id:'org.gnome.desktop.background'});
   assert(bg.get_string('picture-uri')===Gio.File.new_for_path(scene+'/static-background.png').get_uri(),'native background not updated');
   Gio.File.new_for_path(scene+'/static-background.png').copy(Gio.File.new_for_path(out+id+'.png'),Gio.FileCopyFlags.OVERWRITE,null,null);
   await delay(300);const after=await command(ext._socketPath,'status');
   assert(after.frames>before.frames && ext._settings.get_int('fps')===15,'animation or FPS changed');
   results.push({id,pid,workerPid,framesDuring:during.frames,quality:JSON.parse(ext._settings.get_string('runtime-status')).runtimeCaptureQuality,width:pix.get_width(),height:pix.get_height(),framesBefore:before.frames,framesAfter:after.frames,fps:15});
  }
  ext._settings.set_boolean('enabled',false);await wait(()=>!ext._proc);
  GLib.file_set_contents(out+'summary.json',JSON.stringify({passed:true,results},null,2));console.warn('RUNTIME-CAPTURE PASS');
 }catch(error){console.error('RUNTIME-CAPTURE ERROR '+error.message+' '+error.stack);}
 finally{ext.disable();await delay(400);global.context.terminate();}
}
