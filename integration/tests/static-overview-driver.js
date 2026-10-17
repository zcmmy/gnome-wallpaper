import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
const delay=ms=>new Promise(resolve=>GLib.timeout_add(GLib.PRIORITY_DEFAULT,ms,()=>{resolve();return GLib.SOURCE_REMOVE;}));
const assert=(v,m)=>{if(!v)throw new Error(m);};
export async function startTest(ext) {
 const results=[];const out=GLib.getenv('WALLPAPER_TEST_ROOT')+'/reports/static-overview/';
 const check=label=>{const state=ext._staticOverview.snapshot();results.push({label,pid:ext._proc?.get_identifier()??null,...state});console.warn('STATIC-OVERVIEW '+JSON.stringify(results.at(-1)));return state;};
 const capture=async name=>{const file=Gio.File.new_for_path(out+name+'.png');const stream=file.replace(null,false,0,null);try{await new Shell.Screenshot().screenshot(false,stream);}finally{stream.close(null);}};
 const wait=async predicate=>{for(let i=0;i<80;i++){if(predicate())return;await delay(150);}throw new Error('condition timeout');};
 try {
  await delay(2500);Main.overview.hide();await delay(900);
  assert(!ext._proc&&!ext._staticOverview.group,'idle allocated resources');
  Main.overview.showApps();await delay(1800);
  let state=check('static-apps');assert(!ext._proc&&state.active&&state.mapped&&state.backgrounds.every(b=>b.loaded&&b.width>=1200&&b.height>=700),'static background absent');await capture('static-apps');
  ext._settings.set_string('selected-id','3582858114');await delay(1700);
  state=check('static-switch');assert(!ext._proc&&state.active,'static selection lost app background');await capture('static-switch');
  Main.overview.hide();await delay(900);state=check('hidden');assert(!state.active&&!ext._proc,'hidden overview retained resources');
  ext._settings.set_boolean('enabled',true);await wait(()=>ext._rendererReady);
  Main.overview.showApps();await delay(1500);state=check('dynamic-apps');assert(!state.active&&ext._overviewWallpaper?.snapshot().backdrop?.mapped,'static backdrop covers dynamic');await capture('dynamic-apps');
  ext._settings.set_boolean('enabled',false);await wait(()=>!ext._proc);await delay(1000);
  state=check('dynamic-to-static');assert(state.active&&state.mapped&&!ext._pointerBridge,'static backdrop missing after stop');await capture('dynamic-to-static');
  Main.overview.hide();await delay(800);
  for(let i=0;i<3;i++){Main.overview.showApps();await delay(600);Main.overview.hide();await delay(600);assert(!ext._staticOverview.group,'background leak after repeat');}
  const helper=ext._staticOverview;ext.disable();assert(helper.dead&&!helper.group&&!helper.signals.length,'disable leaked signals/actors');
  GLib.file_set_contents(out+'summary.json',JSON.stringify({passed:true,results},null,2));console.warn('STATIC-OVERVIEW PASS');
 }catch(e){console.error('STATIC-OVERVIEW ERROR '+e.message+' '+e.stack);}
 finally {global.context.terminate();}
}
