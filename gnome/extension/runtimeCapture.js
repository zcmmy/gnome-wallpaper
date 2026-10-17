// One explicit live-frame request. No worker process or permanent polling.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import {command} from './rendererClient.js';
import {writeThumbnail} from './library.js';
import {applyStaticWallpaper} from './staticWallpaper.js';

export class RuntimeCapture {
    constructor(manager, send = command) {this.manager=manager;this.send=send;this.job=null;this.result=null;}
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
            directory=scene+'/.capture-live-'+GLib.uuid_string_random();
            const folder=Gio.File.new_for_path(directory);folder.make_directory(null);
            folder.set_attribute_uint32('unix::mode',0o700,Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,null);
            const path=directory+'/frame.png';
            const monitor=Gio.File.new_for_path(directory).monitor_directory(Gio.FileMonitorFlags.NONE,null);
            const job={id,request,scene,path,directory,dest,exists,etag,proc:e._proc,monitor,timer:0};
            this.job=job;this.result={request,state:'capturing'};
            monitor.connect('changed',()=>this.complete(job));
            job.timer=GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT,30,()=>{
                job.timer=0;if(this.job===job)this.finish(job,'error','截图超时，原静态图片未改变。');return GLib.SOURCE_REMOVE;
            });
            m.publish();
            this.send(e._socketPath,'screenshot',{path}).then(()=>this.complete(job)).catch(error=>{
                if(this.job===job)this.finish(job,'error','运行时截图失败：'+error.message);
            });
        } catch(error) {
            if(directory){try{Gio.File.new_for_path(directory).delete(null);}catch(_){}}
            fail(error.message);
        }
    }
    complete(job) {
        if(this.job!==job || !Gio.File.new_for_path(job.path).query_exists(null))return;
        const m=this.manager,e=m.ext,s=m.settings;
        if(m.dead || !s.get_boolean('enabled') || e._proc!==job.proc || e._procStopping ||
            !e._rendererReady || e._resolveScenePath()!==job.scene || s.get_string('selected-id')!==job.id){
            this.cancel();return;
        }
        try {
            // Renderer publishes this path only by atomic rename after encoding.
            GdkPixbuf.Pixbuf.new_from_file(job.path);
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
            this.finish(job,'done',warning || '已用当前动态画面替换静态壁纸。');
            m.reload();
            s.set_int('static-revision',(s.get_int('static-revision')+1)%2147483647);
            m.publish();
        } catch(error) {
            this.finish(job,'error','未替换静态图片：'+error.message);
        }
    }
    cleanup(job) {
        job.monitor.cancel();if(job.timer)GLib.source_remove(job.timer);
        // Removing the private parent prevents a late encoder rename after cancellation.
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
