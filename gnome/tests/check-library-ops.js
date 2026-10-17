import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import {fileOperation,deleteWallpaper} from '../extension/libraryOps.js';
import {readLibrary} from '../extension/library.js';
const assert=(v,m)=>{if(!v)throw new Error(m);};
const temp=GLib.dir_make_tmp('wallpaper-file-test-XXXXXX'),root=temp+'/library',source=temp+'/incoming';
GLib.mkdir_with_parents(root,0o700);GLib.mkdir_with_parents(source,0o700);
function fixture(id,type='scene'){
 const path=source+'/'+id;GLib.mkdir_with_parents(path,0o700);
 GLib.file_set_contents(path+'/project.json',JSON.stringify({title:id,type,file:'scene.json'}));GLib.file_set_contents(path+'/scene.json','{}');
 const pix=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,false,8,32,18);pix.fill(0x336699ff);pix.savev(path+'/static-background.png','png',[],[]);
 return path;
}
async function main(){
 const first=fixture('one'),second=fixture('two');fixture('unsupported','web');
 const linked=fixture('linked');Gio.File.new_for_path(linked+'/escape').make_symbolic_link('/etc',null);
 let result=await fileOperation('import',root,first);assert(result.imported.length===1,'single import');
 result=await fileOperation('import',root,source);assert(result.imported.includes('two')&&result.skipped.includes('one')&&result.errors.length===2,'bulk/duplicate/invalid/symlink handling');
 assert(readLibrary(root).length===2&&Gio.File.new_for_path(first+'/scene.json').query_exists(null),'source modified');
 GLib.file_set_contents(first+'/scene.json','changed');await fileOperation('import',root,first);
 const [,bytes]=GLib.file_get_contents(root+'/one/scene.json');assert(new TextDecoder().decode(bytes)==='{}','duplicate overwrote destination');
 const settings=new Gio.Settings({schema_id:'org.gnome.shell.extensions.wallpaperengine'});settings.set_string('library-root',root);settings.set_string('selected-id','one');settings.set_boolean('enabled',true);settings.set_strv('rotation-ids',['one','two']);settings.set_boolean('rotation-enabled',true);
 settings.set_string('runtime-status',JSON.stringify({active:true,selected:'one',pid:'123',state:'dynamic'}));
 let waited=false;
 const signal=settings.connect('changed::selected-id',()=>{
  if(settings.get_string('selected-id')==='two')GLib.timeout_add(GLib.PRIORITY_DEFAULT,100,()=>{
   assert(Gio.File.new_for_path(root+'/one').query_exists(null),'deleted before old renderer release');waited=true;
   settings.set_string('runtime-status',JSON.stringify({active:true,selected:'two',pid:'456',state:'dynamic'}));return GLib.SOURCE_REMOVE;
  });
 });
 await deleteWallpaper(settings,'one');settings.disconnect(signal);
 assert(waited&&!Gio.File.new_for_path(root+'/one').query_exists(null),'active deletion/release');
 assert(settings.get_boolean('enabled')&&settings.get_string('selected-id')==='two'&&settings.get_strv('rotation-ids').join()==='two','sticky mode or rotation cleanup');
 settings.set_string('runtime-status',JSON.stringify({active:false,pid:null}));
 await deleteWallpaper(settings,'two');assert(readLibrary(root).length===0&&!settings.get_boolean('enabled')&&!settings.get_boolean('rotation-enabled'),'last item cleanup');
 const background=new Gio.Settings({schema_id:'org.gnome.desktop.background'}).get_string('picture-uri-dark');
 assert(background.includes('retained-background')&&Gio.File.new_for_uri(background).query_exists(null),'last static background lost');
 let denied=false;try{await fileOperation('delete',root,'../incoming');}catch(_){denied=true;}assert(denied,'delete traversal allowed');
 print('PASS: single/batch import, duplicate protection, invalid resources, symlinks, active renderer release, sticky mode, rotation cleanup, last-image retention and traversal rejection');
}
const loop=GLib.MainLoop.new(null,false);let failed=null;
main().catch(e=>{failed=e;printerr(e.stack);}).finally(()=>loop.quit());loop.run();
if(failed)throw failed;
