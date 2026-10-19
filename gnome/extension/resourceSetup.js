import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {paths, extensionRoot, initializePaths, backendStatus, assetsReady, readJson, writeJson} from './common/paths.js';
import {refreshFiles} from './libraryOps.js';

export function resourceOperation(request, onProgress=()=>{}, cancellable=null) {
    return new Promise((resolve,reject)=>{
        const proc=Gio.Subprocess.new(['/usr/bin/python3',extensionRoot+'/helpers/dataWorker.py','--root',paths.data],
            Gio.SubprocessFlags.STDIN_PIPE|Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_SILENCE);
        const input=proc.get_stdin_pipe();input.write_all(new TextEncoder().encode(JSON.stringify(request)),null);input.close(null);
        const output=new Gio.DataInputStream({base_stream:proc.get_stdout_pipe()});let report=null,error=null;
        const id=cancellable?.connect(()=>{try{proc.send_signal(15);}catch(_){}});
        const read=()=>output.read_line_async(GLib.PRIORITY_DEFAULT,null,(stream,result)=>{
            try {
                const [line]=stream.read_line_finish_utf8(result);
                if(line!==null){const data=JSON.parse(line);if(data.result)report=data.result;if(data.error)error=data.error;if(data.total!==undefined)onProgress(data);read();return;}
                proc.wait_async(null,(p,r)=>{try{p.wait_finish(r);if(id)cancellable.disconnect(id);output.close(null);
                    if(!p.get_successful()||!report)throw new Error(error||'资源任务未完成');resolve(report);
                }catch(e){reject(e);}});
            }catch(e){try{proc.send_signal(15);}catch(_){}if(id)cancellable.disconnect(id);reject(e);}
        });read();
    });
}
function confirm(window,title,body) {
    const dialog=new Adw.AlertDialog({heading:title,body});dialog.add_response('cancel','取消');dialog.add_response('continue','继续');dialog.set_close_response('cancel');
    return new Promise(resolve=>dialog.choose(window,null,(d,r)=>resolve(d.choose_finish(r)==='continue')));
}
async function stopPlayback(settings) {
    settings.set_boolean('enabled',false);
    for(let i=0;i<80;i++){
        let state={};try{state=JSON.parse(settings.get_string('runtime-status'));}catch(_){}
        if(!state.pid&&!state.capturing)return;
        await new Promise(r=>GLib.timeout_add(0,100,()=>{r();return false;}));
    }
    throw new Error('旧播放或截图任务尚未退出，请稍后重试');
}
export function addResourceSetup(window,page,settings) {
    let initializationError='';try{initializePaths(settings);}catch(e){initializationError=e.message;}
    const group=new Adw.PreferencesGroup({title:'资源准备',description:'程序已随完整插件安装；请导入你拥有的公共 assets 和壁纸。来源文件保持原样。'});page.add(group);
    const backend=new Adw.ActionRow({title:'内置渲染器'}),assets=new Adw.ActionRow({title:'公共 assets'}),library=new Adw.ActionRow({title:'壁纸数据'});
    group.add(backend);group.add(assets);group.add(library);
    const progress=new Gtk.ProgressBar({show_text:true,visible:false});group.add(progress);
    let active=null;
    const cancel=new Gtk.Button({label:'取消导入',visible:false});cancel.connect('clicked',()=>active?.cancel());group.add(cancel);
    const toast=message=>window.add_toast(new Adw.Toast({title:message,timeout:6}));
    const refresh=()=>{const state=backendStatus();backend.subtitle=initializationError|| (state.ready?'已内置 · '+state.version:state.error);assets.subtitle=assetsReady()?'已导入':'尚未导入；静态模式仍可使用';library.subtitle=paths.data;};
    async function execute(request) {
        if(active)throw new Error('已有资源任务正在运行');
        const plan=await resourceOperation({...request,plan:true});
        if(!await confirm(window,'导入资源？',`将复制约 ${(plan.bytes/1048576).toFixed(1)} MiB，跳过 ${plan.skipped.length} 个已有项目。`+(request.operation==='import'?'':'\n此操作会停止动态播放与截图，完成后保持静态模式。')))return null;
        if(request.operation!=='import')await stopPlayback(settings);
        active=new Gio.Cancellable();progress.visible=true;cancel.visible=true;
        try {
            const result=await resourceOperation(request,data=>{progress.fraction=data.total?Math.min(1,data.progress/data.total):0;progress.text=`${(data.progress/1048576).toFixed(1)} / ${(data.total/1048576).toFixed(1)} MiB`;},active);
            refreshFiles(settings);toast('资源导入完成');return result;
        }finally{active=null;progress.visible=false;cancel.visible=false;refresh();}
    }
    const choose=(operation)=>new Gtk.FileDialog({title:operation==='assets'?'选择自备的 assets 目录':'选择单张壁纸目录或包含多张壁纸的目录'}).select_folder(window,null,(d,r)=>{
        let folder;try{folder=d.select_folder_finish(r)?.get_path();}catch(_){return;}if(!folder)return;
        (async()=>{
            if(operation==='assets'&&assetsReady()&&!await confirm(window,'替换公共资源？','现有 assets 将在完整复制并校验后替换；壁纸与用户静态图保留。'))return;
            await execute(operation==='assets'?{operation,assets:folder,replace:assetsReady()}:{operation,source:folder});
        })().catch(e=>toast(e.message));
    });
    const assetButton=new Gtk.Button({label:'导入 / 替换…',valign:Gtk.Align.CENTER});assetButton.connect('clicked',()=>choose('assets'));assets.add_suffix(assetButton);
    const open=new Gtk.Button({label:'打开数据目录',valign:Gtk.Align.CENTER});open.connect('clicked',()=>Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(paths.data).get_uri(),null));library.add_suffix(open);
    const usage=new Gtk.Button({label:'检查占用',valign:Gtk.Align.CENTER});usage.connect('clicked',()=>resourceOperation({operation:'status'}).then(r=>{library.subtitle=`${paths.data} · 壁纸 ${(r.bytes/1048576).toFixed(1)} MiB`;}).catch(e=>toast(e.message)));library.add_suffix(usage);
    const migration=new Adw.ActionRow({title:'迁移旧版资源',subtitle:'复制旧 runtime 的资源到管理目录，保留旧目录、静态图、选择、FPS 与轮换设置。'});group.add(migration);
    const migrate=new Gtk.Button({label:'检查并迁移…',valign:Gtk.Align.CENTER});migration.add_suffix(migrate);
    migrate.connect('clicked',()=>{
        (async()=>{
            const old=readJson(paths.state+'/legacy-settings.json');
            const result=await execute({operation:'migrate',assets:old['assets-path'],source:old['library-root']});
            if(result){
                if(GLib.file_test(paths.library+'/'+old['selected-id']+'/project.json',GLib.FileTest.IS_REGULAR))settings.set_string('selected-id',old['selected-id']);
                writeJson(paths.state+'/migration.json',{version:1,completed:true,at:new Date().toISOString()});
                migrate.sensitive=false;refreshFiles(settings);
            }
        })().catch(e=>toast('迁移未完成：'+e.message));
    });
    migrate.sensitive=GLib.file_test(paths.state+'/legacy-settings.json',GLib.FileTest.IS_REGULAR)&&!GLib.file_test(paths.state+'/migration.json',GLib.FileTest.IS_REGULAR);
    window.connect('close-request',()=>{if(active){toast('请等待任务结束，或先取消导入');return true;}return false;});
    refresh();return {choose,execute,refresh,group,backend,assets,library,progress,cancel};
}
