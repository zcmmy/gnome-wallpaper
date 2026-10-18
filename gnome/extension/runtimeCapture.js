// Explicit high-quality replacement; the playing renderer is never reconfigured.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import {writeThumbnail} from './library.js';
import {applyStaticWallpaper} from './staticWallpaper.js';

const captureWorker = Gio.File.new_for_uri(import.meta.url).get_parent().get_child('captureWorker.py').get_path();

export class RuntimeCapture {
    constructor(manager, launch = null) {
        this.manager=manager;this.launch=launch ?? (job=>this.launchWorker(job));this.job=null;this.result=null;
    }
    launchWorker(job) {
        const s=this.manager.settings;
        const expand=value=>value.startsWith('~/') ? GLib.get_home_dir()+value.slice(1) : value;
        const renderer=expand(s.get_string('wallpaperengine-path'));
        const executable=GLib.path_is_absolute(renderer) ? renderer : GLib.find_program_in_path(renderer);
        if(!executable)throw new Error('找不到壁纸渲染程序');
        job.worker=Gio.Subprocess.new(['/usr/bin/python3',captureWorker,
            '--renderer',executable,'--assets',expand(s.get_string('assets-path')),
            '--scene',job.scene,'--output',job.path,'--scaling',s.get_string('scaling'),'--quality','high'],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
        return new Promise((resolve,reject)=>{
            job.worker.communicate_utf8_async(null,null,(proc,result)=>{
                job.worker=null;
                try {
                    const [,out,err]=proc.communicate_utf8_finish(result);
                    let report={};try{report=JSON.parse(out);}catch(_){}
                    if(!proc.get_successful())throw new Error(String(report.error || err || '截图任务退出').slice(0,300));
                    if(report.quality!=='high' || report.size?.[0]!==1920 || report.size?.[1]!==1080)
                        throw new Error('截图任务未返回有效的高质量结果');
                    resolve();
                } catch(error) {reject(error);}
            });
        });
    }
    start(id, request) {
        const m=this.manager,e=m.ext,s=m.settings;
        if (this.job || m.capture) return; // Repeated clicks do not cancel a valid request.
        const fail=message=>{this.result={request,state:'error',message};m.publish();};
        if (m.dead || !s.get_boolean('enabled') || !e._rendererReady || !e._proc || e._procStopping ||
            id!==s.get_string('selected-id') || !m.current?.supported) {
            fail('请等待所选壁纸进入动态模式后再截图。');return;
        }
        const scene=e._resolveScenePath(), dest=Gio.File.new_for_path(scene+'/static-background.png');
        let directory;
        try {
            const exists=dest.query_exists(null);
            const info=exists?dest.query_info('standard::type,etag::value',Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,null):null;
            if(info && info.get_file_type()!==Gio.FileType.REGULAR)throw new Error('静态图片不是普通文件，未替换。');
            const etag=info?.get_attribute_string('etag::value');
            if(exists && !etag)throw new Error('无法安全识别原静态图片，未替换。');
            directory=scene+'/.capture-hq-'+GLib.uuid_string_random();
            const folder=Gio.File.new_for_path(directory);folder.make_directory(null);
            folder.set_attribute_uint32('unix::mode',0o700,Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,null);
            const path=directory+'/frame.png';
            const job={id,request,scene,path,directory,dest,exists,etag,proc:e._proc,worker:null,timer:0};
            this.job=job;this.result={request,state:'capturing'};
            job.timer=GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT,210,()=>{
                job.timer=0;if(this.job===job)this.finish(job,'error','截图超时，原静态图片未改变。');return GLib.SOURCE_REMOVE;
            });
            m.publish();
            Promise.resolve(this.launch(job)).then(()=>{
                // Wait for the private renderer and compositor to exit before publishing.
                if(this.job===job)this.complete(job);else this.cleanup(job);
            }).catch(error=>{
                if(this.job===job)this.finish(job,'error','高质量截图失败：'+error.message);
                else this.cleanup(job);
            });
        } catch(error) {
            if(this.job){this.finish(this.job,'error',error.message);return;}
            if(directory){try{Gio.File.new_for_path(directory).delete(null);}catch(_){}}
            fail(error.message);
        }
    }
    complete(job) {
        if(this.job!==job)return;
        const m=this.manager,e=m.ext,s=m.settings;
        if(m.dead || !s.get_boolean('enabled') || e._proc!==job.proc || e._procStopping ||
            !e._rendererReady || e._resolveScenePath()!==job.scene || s.get_string('selected-id')!==job.id){
            this.cancel();return;
        }
        try {
            // The worker exits only after validating and atomically publishing the PNG.
            const image=GdkPixbuf.Pixbuf.new_from_file(job.path);
            if(image.get_width()!==1920 || image.get_height()!==1080)throw new Error('高质量图片尺寸不正确');
            const file=Gio.File.new_for_path(job.path);
            if(job.exists){
                if(!job.dest.query_exists(null))throw new Error('截图期间静态图片已改变，未覆盖新的选择。');
                const [,bytes]=file.load_contents(null);
                job.dest.replace_contents(bytes,job.etag,false,Gio.FileCreateFlags.REPLACE_DESTINATION,null);
            } else {
                file.move(job.dest,Gio.FileCopyFlags.NONE,null,null);
            }
            let warning='';
            try{writeThumbnail(job.scene);}catch(_){warning='缩略图未更新；静态图片已保存。';}
            try{if(!applyStaticWallpaper(job.scene,s.get_string('scaling')))warning='静态图片已保存，但系统背景设置不可写。';}
            catch(_){warning='静态图片已保存，但系统背景更新失败。';}
            this.finish(job,'done',warning || '已用高质量截图替换静态壁纸，动态播放继续。');
            m.reload();
            s.set_int('static-revision',(s.get_int('static-revision')+1)%2147483647);
            m.publish();
        } catch(error) {
            this.finish(job,'error','未替换静态图片：'+error.message);
        }
    }
    cleanup(job) {
        if(job.timer){GLib.source_remove(job.timer);job.timer=0;}
        // Only signal the private worker. Its handler reaps its own children.
        // Completion also cleans again, covering a publish/cancel race.
        try{job.worker?.send_signal(15);}catch(_){}
        for(const path of [job.path,job.path+'.tmp',job.directory]){
            try{Gio.File.new_for_path(path).delete(null);}catch(_){}
        }
    }
    finish(job,state,message) {
        if(this.job!==job)return;
        this.job=null;this.cleanup(job);this.result={request:job.request,state,message};this.manager.publish();
    }
    cancel() {if(this.job)this.finish(this.job,'cancelled','截图已取消，保留原静态图片。');}
}
