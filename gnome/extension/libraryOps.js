import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {readLibrary, imageInfo} from './library.js';
import {applyStaticWallpaper} from './staticWallpaper.js';
const worker=Gio.File.new_for_uri(import.meta.url).get_parent().get_child('libraryWorker.py').get_path();
export function fileOperation(operation,root,value) {
    return new Promise((resolve,reject)=>{
        const proc=Gio.Subprocess.new(['/usr/bin/python3',worker,operation,root,value],Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE);
        proc.communicate_utf8_async(null,null,(p,result)=>{
            try {const [,out,err]=p.communicate_utf8_finish(result);const data=JSON.parse(out);
                if(!p.get_successful())throw new Error(data.error||err||'文件操作失败');resolve(data);
            }catch(e){reject(e);}
        });
    });
}
export function refreshFiles(settings) {
    // This existing file-content signal reloads the catalog without restarting
    // an unrelated dynamic wallpaper, unlike a playback selection change.
    settings.set_int('static-revision',(settings.get_int('static-revision')+1)%2147483647);
}
function releaseRenderer(settings,oldPid) {
    if(!oldPid)return Promise.resolve();
    return new Promise((resolve,reject)=>{
        let signal=0,timer=0,done=false;
        const finish=error=>{if(done)return;done=true;if(signal)settings.disconnect(signal);if(timer)GLib.source_remove(timer);error?reject(error):resolve();};
        const check=()=>{try{const state=JSON.parse(settings.get_string('runtime-status'));if(state.active===false||!state.pid||state.pid!==oldPid)finish();}catch(_){}};
        signal=settings.connect('changed::runtime-status',check);
        timer=GLib.timeout_add(GLib.PRIORITY_DEFAULT,6000,()=>{timer=0;finish(new Error('旧渲染器尚未退出，未删除壁纸。请关闭动态后重试。'));return GLib.SOURCE_REMOVE;});
        check();
    });
}
async function retainStill(item) {
    if(!imageInfo(item.still))return;
    const path=GLib.build_filenamev([GLib.get_user_state_dir(),'gnome-wallpaper','retained-background']);
    GLib.mkdir_with_parents(path,0o700);
    await new Promise((resolve,reject)=>Gio.File.new_for_path(item.still).copy_async(Gio.File.new_for_path(path+'/static-background.png'),Gio.FileCopyFlags.OVERWRITE,GLib.PRIORITY_DEFAULT,null,null,(file,result)=>{try{file.copy_finish(result);resolve();}catch(e){reject(e);}}));
    applyStaticWallpaper(path);
}
export async function deleteWallpaper(settings,id,connected=true) {
    const root=settings.get_string('library-root');
    const items=readLibrary(root),item=items.find(i=>i.id===id);
    if(!item)throw new Error('壁纸已不存在，请刷新列表');
    const isCurrent=settings.get_string('selected-id')===id;
    if(isCurrent){
        const others=items.filter(i=>i.id!==id),fallback=others.find(i=>i.ready)??others[0];
        let status={};try{status=JSON.parse(settings.get_string('runtime-status'));}catch(_){}
        if(!fallback?.ready)await retainStill(item);
        else applyStaticWallpaper(fallback.path,settings.get_string('scaling'));
        if(!fallback){settings.set_boolean('rotation-enabled',false);settings.set_boolean('enabled',false);}
        settings.set_string('selected-id',fallback?.id??'');
        if(connected && status.active)await releaseRenderer(settings,status.pid);
    }
    if(settings.get_string('library-root')!==root || settings.get_string('selected-id')===id)throw new Error('壁纸选择发生变化，已取消删除');
    const result=await fileOperation('delete',root,id);
    settings.set_strv('rotation-ids',settings.get_strv('rotation-ids').filter(value=>value!==id));
    settings.set_string('rotation-state','{}');
    refreshFiles(settings);
    return result;
}
