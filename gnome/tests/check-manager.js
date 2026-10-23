import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import {makeOrder, advance} from '../extension/rotation.js';
import {readLibrary, scenePath, replaceStaticImage} from '../extension/library.js';
import {WallpaperManager} from '../extension/manager.js';
function assert(v,m){if(!v)throw new Error(m);}
const ids=['a','b','c','d'];
assert(JSON.stringify(makeOrder(ids,'shuffle',123))===JSON.stringify(makeOrder(ids,'shuffle',123)),'not deterministic');
for(let seed=1;seed<100;seed++){const order=makeOrder(ids,'shuffle',seed,'a').order;assert(new Set(order).size===4&&order[0]!=='a','shuffle repeats or crosses boundary');}
let state={},current=null,seen=[];
for(let n=0;n<12;n++){state=advance(ids,'shuffle',state,current);current=state.id;seen.push(current);}
for(let n=0;n<12;n+=4)assert(new Set(seen.slice(n,n+4)).size===4,'cycle repetition');
assert(advance(ids,'ordered',{},'d').id==='a','ordered wrap');
assert(advance(ids,'ordered',{},'a',-1).id==='d','previous wrap');
assert(advance([], 'shuffle',state,current).id===null,'empty list');
assert(advance(['b'],'shuffle',state,'b').id==='b','one-item list');
assert(advance(['a','c'],'shuffle',state,'b').order.every(i=>i!=='b'),'deleted item remains');
assert(advance(ids,'ordered',{signature:JSON.stringify([ids,'ordered'])},'a').id==='b','corrupt state not repaired');
assert(scenePath('/tmp','../x')===null&&scenePath('/tmp','..')===null,'path escape');
const root=GLib.getenv('TEST_LIBRARY');GLib.mkdir_with_parents(root+'/item',0o700);
const scene=root+'/item';GLib.file_set_contents(scene+'/project.json',JSON.stringify({title:'Test <literal>',type:'Scene'}));
const red=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,false,8,32,18);red.fill(0xff0000ff);red.savev(root+'/red.png','png',[],[]);
const blue=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,false,8,32,18);blue.fill(0x0000ffff);blue.savev(root+'/blue.png','png',[],[]);
assert(readLibrary(root)[0].type==='scene'&&!readLibrary(root)[0].ready,'catalog normalization');
replaceStaticImage(scene,root+'/red.png');assert(readLibrary(root)[0].ready,'replacement not discovered');
Gio.File.new_for_path(scene+'/static-background.png').delete(null);
const settings=new Gio.Settings({schema_id:'org.gnome.shell.extensions.wallpaperengine'});settings.set_string('library-root',root);settings.set_string('selected-id','item');
const ext={_settings:settings,_resolveScenePath:()=>scene,_proc:null,_rendererReady:false};
const loop=GLib.MainLoop.new(null,false);
const manager=new WallpaperManager(ext);
let stops=0,starts=0;
ext._stopEngine=()=>stops++;ext._startEngine=()=>starts++;
settings.set_string('selected-id','');manager.items=[];manager.select();
let fresh=JSON.parse(settings.get_string('runtime-status'));
assert(fresh.state==='static'&&!fresh.error&&!fresh.pid&&!fresh.dynamic,'fresh selection reported as missing wallpaper');
assert(stops===1&&starts===0&&!manager.timer&&!manager.watchdog,'fresh setup started background work');
manager.reload();manager.select();
assert(!JSON.parse(settings.get_string('runtime-status')).error,'import without selection reported as missing wallpaper');
settings.set_string('selected-id','missing');manager.select();
assert(JSON.parse(settings.get_string('runtime-status')).state==='error','missing saved selection must still report an error');
settings.set_string('selected-id','item');
const temporary=manager.prepareCapture(scene);assert(temporary,'missing image did not request capture');
// The user supplies a red image while a blue automatic capture is in flight.
replaceStaticImage(scene,root+'/red.png');
Gio.File.new_for_path(root+'/blue.png').copy(Gio.File.new_for_path(temporary),0,null,null);
GLib.timeout_add(GLib.PRIORITY_DEFAULT,900,()=>{
 try{
  const pixels=GdkPixbuf.Pixbuf.new_from_file(scene+'/static-background.png').get_pixels();
  assert(pixels[0]===255&&pixels[2]===0,'automatic capture overwrote user image');
  assert(!manager.capture,'capture watcher leaked');
  assert(manager.prepareCapture(scene)===null,'existing still triggered capture');
  assert(!manager.timer&&!manager.watchdog,'static controller has work timer');
  manager.destroy();
  print('PASS: deterministic rotation/recovery, catalog normalization, custom image import, one-shot capture cleanup and user-image precedence');
 }catch(e){printerr(e.message);globalThis.failed=true;}
 loop.quit();return GLib.SOURCE_REMOVE;
});loop.run();if(globalThis.failed)throw new Error('manager test failed');
