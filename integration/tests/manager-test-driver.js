import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {command} from './rendererClient.js';
export function startTest(ext) {
 let tick=0,pid=null,failed=false;
 const root=GLib.getenv('WALLPAPER_TEST_ROOT');
 const snapshot=label=>{const state=JSON.parse(ext._settings.get_string('runtime-status'));console.warn('MANAGER-TEST '+JSON.stringify({label,...state,rotationTimer:ext._manager.timer,overview:!!ext._overviewWallpaper,pointer:!!ext._pointerBridge}));};
 const assert=(ok,why)=>{if(!ok)throw new Error(why);};
 GLib.timeout_add(GLib.PRIORITY_DEFAULT,1000,()=>{
  try{
   tick++;
   if(tick===3){Main.overview.hide();assert(!ext._proc&&!ext._overviewWallpaper&&!ext._pointerBridge,'static mode allocates renderer resources');snapshot('initial-static');}
   if(tick===4)ext._settings.set_string('selected-id',GLib.getenv('WALLPAPER_TEST_SCENE_B'));
   if(tick===5){assert(!ext._proc,'static selection started renderer');assert(new Gio.Settings({schema_id:'org.gnome.desktop.background'}).get_string('picture-uri-dark').includes(GLib.getenv('WALLPAPER_TEST_SCENE_B')),'static was not applied');snapshot('static-switch');}
   if(tick===6)ext._settings.set_boolean('enabled',true);
   if(tick===12){assert(ext._rendererActor,'dynamic not adopted');pid=ext._proc.get_identifier();snapshot('dynamic');ext._settings.set_int('fps',12);ext._settings.set_int('fps',13);ext._settings.set_int('fps',12);}
   if(tick===14){assert(ext._proc.get_identifier()===pid,'fps restarted renderer');command(ext._socketPath,'status').then(result=>{assert(result.fps===12,'live fps cap not applied');console.warn('MANAGER-FPS '+JSON.stringify(result));}).catch(e=>{failed=true;console.error('MANAGER-TEST ERROR '+e.message+' '+e.stack);});snapshot('fps-live');}
   if(tick===15)ext._settings.set_string('selected-id',GLib.getenv('WALLPAPER_TEST_SCENE_A'));
   if(tick===20){assert(ext._rendererActor&&ext._proc.get_identifier()!==pid&&ext._settings.get_boolean('enabled'),'dynamic intent lost during switch');snapshot('dynamic-switch');ext._settings.set_boolean('enabled',false);}
   if(tick===23){assert(!ext._proc&&!ext._overviewWallpaper&&!ext._pointerBridge,'static did not release resources');snapshot('stopped-static');ext._settings.set_boolean('rotation-enabled',true);ext._settings.set_double('rotation-next-at',Date.now()/1000-2);ext._manager.arm(false);}
   if(tick===26){assert(ext._settings.get_string('selected-id')===GLib.getenv('WALLPAPER_TEST_SCENE_B')&&!ext._proc,'static rotation failed');snapshot('static-rotation');ext._settings.set_boolean('rotation-enabled',false);ext._settings.set_string('selected-id','capture-fixture');}
   if(tick===27){assert(!ext._proc&&!ext._manager.capture,'missing image caused automatic renderer');snapshot('missing-static');ext._settings.set_boolean('enabled',true);}
   if(tick===33){pid=ext._proc.get_identifier();const [,raw]=GLib.file_get_contents('/proc/'+pid+'/cmdline');assert(!new TextDecoder().decode(raw).includes('--screenshot'),'normal renderer contains capture flags');snapshot('hq-capturing');}
   if(tick===60){assert(ext._proc.get_identifier()===pid,'HQ capture restarted normal renderer');assert(ext._rendererActor,'capture renderer not running');assert(Gio.File.new_for_path(ext._resolveScenePath()+'/static-background.png').query_exists(null),'missing still not captured');assert(!ext._manager.capture,'capture monitor remained');snapshot('captured');ext._settings.set_boolean('enabled',false);}
   if(tick===62){ext._settings.set_boolean('enabled',true);ext._settings.set_string('selected-id',GLib.getenv('WALLPAPER_TEST_SCENE_B'));ext._settings.set_string('selected-id',GLib.getenv('WALLPAPER_TEST_SCENE_A'));ext._settings.set_boolean('enabled',false);}
   if(tick===67){assert(!ext._proc&&!ext._overviewWallpaper&&!ext._pointerBridge&&!ext._manager.timer&&!ext._manager.capture,'idle resources remain');snapshot('complete');assert(!failed,'async assertion failed');global.context.terminate();return GLib.SOURCE_REMOVE;}
  }catch(e){console.error('MANAGER-TEST ERROR '+e.message+' '+e.stack);global.context.terminate();return GLib.SOURCE_REMOVE;}
  return GLib.SOURCE_CONTINUE;
 });
}
