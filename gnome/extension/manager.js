import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import {readLibrary, scenePath, imageInfo, writeThumbnail} from './library.js';
import {applyStaticWallpaper} from './staticWallpaper.js';
import {advance} from './rotation.js';
import {command} from './rendererClient.js';
import {RuntimeCapture} from './runtimeCapture.js';
const captureWorker = Gio.File.new_for_uri(import.meta.url).get_parent().get_child('captureWorker.py').get_path();

export class WallpaperManager {
    constructor(extension) {
        this.ext = extension;
        this.settings = extension._settings;
        this.timer = 0; this.capture = null; this.watchdog = 0; this.dead = false;
        this.error = ''; this.items = []; this.suspended = false;
        this.runtimeCapture = new RuntimeCapture(this);
        this.reload();
        this.dbus = Gio.DBusExportedObject.wrapJSObject(`<node><interface name="org.wallpaper.Manager"><method name="Snapshot"><arg type="s" direction="out"/></method></interface></node>`, {Snapshot:() => this.settings.get_string('runtime-status')});
        this.dbus.export(Gio.DBus.session, '/org/gnome/Shell/WallpaperManager');
    }
    reload() {
        try {this.items = readLibrary(this.settings.get_string('library-root'));}
        catch (e) {this.items = []; this.error = '读取壁纸库失败：' + e.message;}
    }
    start() {this.select(); this.arm(false);}
    get current() {return this.items.find(i => i.id === this.settings.get_string('selected-id'));}
    publish(state = null) {
        if (this.dead) return;
        this.ext._staticOverview?.sync();
        const e = this.ext;
        const status = {version:12, active:true, selected:this.settings.get_string('selected-id'),
            state:state ?? (e._procStopping ? 'stopping' : e._rendererReady ? 'dynamic' : e._proc ? 'loading' : this.error ? 'error' : 'static'),
            dynamic:this.settings.get_boolean('enabled'), pid:e._proc?.get_identifier() ?? null,
            fps:this.settings.get_int('fps'), staticOverview:!!e._staticOverview, captureQuality:'4k-to-1080p', error:this.error, capturing:!!this.capture || !!this.runtimeCapture?.job, runtimeCaptureSupported:true, runtimeCapture:this.runtimeCapture?.result ?? null,
            staticReady:!!imageInfo(e._resolveScenePath() + '/static-background.png')};
        const value = JSON.stringify(status);
        if (this.settings.get_string('runtime-status') !== value) this.settings.set_string('runtime-status', value);
    }
    changed(key) {
        if (this.dead) return;
        if (['runtime-status','rotation-state','rotation-next-at'].includes(key)) return;
        if (key === 'manager-command') {
            const value = this.settings.get_string(key);
            if (value.startsWith('{')) {
                try {const request=JSON.parse(value);if(request.action==='capture-static' && typeof request.id==='string' && typeof request.request==='string')this.runtimeCapture.start(request.id,request.request);}catch(_){}
                return;
            }
            const cmd = value.split(':')[0];
            if (cmd === 'next' || cmd === 'previous') this.next(cmd === 'next' ? 1 : -1);
            if (cmd === 'retry') this.select();
            return;
        }
        if (key.startsWith('rotation-')) {this.arm(true); return;}
        if (key === 'static-revision') {
            this.runtimeCapture.cancel();
            this.reload();
            try {applyStaticWallpaper(this.ext._resolveScenePath(), this.settings.get_string('scaling')); this.error = '';}
            catch (e) {this.error = e.message;}
            this.arm(false); this.publish(); return;
        }
        if (key === 'fps') {
            this.publish();
            this.applyFps();
            return;
        }
        if (key === 'library-root' || key === 'library-revision') this.reload();
        if (['selected-id','library-root','library-revision','enabled','wallpaper-id','scaling','monitor-index','assets-path','wallpaperengine-path','engine','mute','volume','video-path'].includes(key)) {
            this.select();
            if (['selected-id','library-root','library-revision'].includes(key)) this.arm(true);
        }
    }
    async applyFps() {
        if (this.fpsBusy || !this.ext._proc || this.ext._procStopping) return;
        this.fpsBusy = true;
        const proc = this.ext._proc;
        let sent;
        try {
            do {
                sent = this.settings.get_int('fps');
                await command(this.ext._socketPath, 'set-fps', {fps:sent});
            } while (!this.dead && this.ext._proc === proc && !this.ext._procStopping && sent !== this.settings.get_int('fps'));
        } catch (e) {
            if (!this.dead && this.ext._proc === proc) {
                this.error = '帧率命令未确认，重新开启动态后生效：' + e.message; this.publish();
            }
        } finally {
            this.fpsBusy = false;
            if (!this.dead && this.ext._proc && this.ext._proc !== proc) this.applyFps();
        }
    }
    select() {
        const e = this.ext;
        this.error = '';
        this.runtimeCapture.cancel(); this.cancelCapture(); this.clearWatchdog();
        if (e._restartTimeoutId) {GLib.source_remove(e._restartTimeoutId); e._restartTimeoutId = 0;}
        const root = this.settings.get_string('library-root');
        const scene = e._resolveScenePath();
        if (root && !this.current) {
            e._restartPending = false; e._stopEngine();
            this.error = '所选壁纸不存在，请刷新壁纸库或选择其他壁纸。'; this.publish(); return;
        }
        try {
            const applied = applyStaticWallpaper(scene, this.settings.get_string('scaling'));
            if (!applied && !this.settings.get_boolean('enabled')) this.error = '缺少静态图片。请选择图片，或明确开启动态以生成一次截图。';
        } catch (err) {this.error = err.message;}
        // Release the old surface immediately; the native still is independent.
        if (e._rendererActor) e._rendererActor.opacity = 0;
        e._restartPending = this.settings.get_boolean('enabled');
        e._crashRetries = 0;
        e._stopEngine();
        if (!e._proc && e._restartPending) e._startEngine();
        this.publish();
    }
    launched() {
        this.clearWatchdog();
        this.watchdog = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 45, () => {
            this.watchdog = 0;
            if (!this.ext._rendererReady) {
                this.ext._restartPending = false; this.ext._stopEngine();
                this.error = '动态壁纸加载超时，保留静态背景。可重试或选择其他壁纸。'; this.publish();
            }
            return GLib.SOURCE_REMOVE;
        });
        this.publish();
    }
    adopted() {this.clearWatchdog(); this.startCapture(this.ext._resolveScenePath()); this.publish();}
    clearWatchdog() {if (this.watchdog) GLib.source_remove(this.watchdog); this.watchdog = 0;}
    failed(message) {this.clearWatchdog(); this.runtimeCapture.cancel(); this.cancelCapture(); this.error = message; this.publish('error');}

    startCapture(scene) {
        if (this.dead || this.capture || this.runtimeCapture.job || !this.settings.get_boolean('enabled')) return;
        const path = this.prepareCapture(scene);
        if (!path) return;
        const capture = this.capture;
        const expand = value => value.startsWith('~/') ? GLib.get_home_dir() + value.slice(1) : value;
        try {
            const renderer = expand(this.settings.get_string('wallpaperengine-path'));
            const executable = GLib.path_is_absolute(renderer) ? renderer : GLib.find_program_in_path(renderer);
            if (!executable) throw new Error('找不到壁纸渲染程序');
            capture.proc = Gio.Subprocess.new(['/usr/bin/python3', captureWorker,
                '--renderer', executable, '--assets', expand(this.settings.get_string('assets-path')),
                '--scene', scene, '--output', path, '--scaling', this.settings.get_string('scaling')],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            capture.proc.communicate_utf8_async(null, null, (proc, result) => {
                try {
                    const [, out, err] = proc.communicate_utf8_finish(result);
                    capture.proc = null;
                    if (this.capture !== capture) return;
                    if (!proc.get_successful()) {
                        let detail = err;
                        try {detail = JSON.parse(out).error || detail;} catch (_) {}
                        this.cancelCapture();
                        this.error = '高质量静态截图失败，可重试或指定图片：' + String(detail).slice(0, 300);
                        this.publish();
                    }
                } catch (error) {
                    if (this.capture !== capture) return;
                    this.cancelCapture(); this.error = '高质量静态截图失败：' + error.message; this.publish();
                }
            });
        } catch (error) {
            this.cancelCapture(); this.error = '无法启动高质量截图：' + error.message; this.publish();
        }
    }

    // Only called while explicitly launching dynamic mode, and only if no still exists.
    prepareCapture(scene) {
        this.cancelCapture();
        if (!scene || !GLib.path_is_absolute(scene) || imageInfo(scene + '/static-background.png')) return null;
        const folder = Gio.File.new_for_path(scene);
        if (folder.query_file_type(0,null) !== Gio.FileType.DIRECTORY) return null;
        const path = scene + '/.capture-' + GLib.uuid_string_random() + '.png';
        const monitor = folder.monitor_directory(Gio.FileMonitorFlags.NONE, null);
        const capture = {path, scene, monitor, timer:0, settle:0, proc:null}; this.capture = capture;
        monitor.connect('changed', (_monitor, file, _other, event) => {
            if (this.capture !== capture || file.get_path() !== path || event === Gio.FileMonitorEvent.DELETED) return;
            if (capture.settle) GLib.source_remove(capture.settle);
            capture.settle = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 250, () => {
                capture.settle = 0;
                if (this.capture !== capture) return GLib.SOURCE_REMOVE;
                try {
                    // Full decoding validates that the writer has finished, not just the PNG header.
                    GdkPixbuf.Pixbuf.new_from_file(path);
                    const dest = Gio.File.new_for_path(scene + '/static-background.png');
                    // A user replacement made while capturing always wins.
                    if (!dest.query_exists(null)) Gio.File.new_for_path(path).move(dest, Gio.FileCopyFlags.NONE, null, null);
                    this.cancelCapture();
                    if (!imageInfo(dest.get_path())) {
                        this.error = '已有静态文件无法读取。为保护用户文件，未覆盖；请重新选择静态图片。'; this.publish();
                        return GLib.SOURCE_REMOVE;
                    }
                    try {writeThumbnail(scene);} catch (_) {}
                    this.reload();
                    if (this.ext._resolveScenePath() === scene) applyStaticWallpaper(scene, this.settings.get_string('scaling'));
                    this.error = ''; this.publish();
                    this.settings.set_int('static-revision', (this.settings.get_int('static-revision') + 1) % 2147483647);
                } catch (_) { /* Wait for another write event or the bounded timeout. */ }
                return GLib.SOURCE_REMOVE;
            });
        });
        capture.timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 210, () => {
            capture.timer = 0;
            if (this.capture === capture) {this.cancelCapture(); this.error = '辅助截图未完成。可指定静态图片，或重新开启动态再试。'; this.publish();}
            return GLib.SOURCE_REMOVE;
        });
        return path;
    }
    cancelCapture() {
        const c = this.capture; this.capture = null;
        if (!c) return;
        c.monitor.cancel();
        // SIGTERM lets the worker reap its private compositor and renderer.
        try {c.proc?.send_signal(15);} catch (_) {}
        if (c.timer) GLib.source_remove(c.timer);
        if (c.settle) GLib.source_remove(c.settle);
        try {Gio.File.new_for_path(c.path).delete(null);} catch (_) {}
        // A finishing write may race cancellation; remove its temporary output after reaping.
        c.proc?.wait_async(null, (proc, result) => {
            try {proc.wait_finish(result);} catch (_) {}
            try {Gio.File.new_for_path(c.path).delete(null);} catch (_) {}
        });
    }
    eligible() {
        const valid = new Set(this.items.filter(i => i.ready && i.supported).map(i => i.id));
        const requested = this.settings.get_boolean('rotation-all') ? this.items.map(i => i.id) : this.settings.get_strv('rotation-ids');
        return [...new Set(requested)].filter(id => valid.has(id));
    }
    next(direction = 1) {
        this.reload();
        const ids = this.eligible();
        if (!ids.length) {this.error = '轮换列表中没有已准备静态图片的壁纸。'; this.publish(); this.arm(true); return;}
        let saved; try {saved = JSON.parse(this.settings.get_string('rotation-state'));} catch (_) {saved = {};}
        if (!saved.seed) saved.seed = (GLib.get_real_time() % 4294967295) >>> 0;
        const next = advance(ids, this.settings.get_string('rotation-mode'), saved, this.settings.get_string('selected-id'), direction);
        this.settings.set_string('rotation-state', JSON.stringify(next));
        if (next.id !== this.settings.get_string('selected-id')) this.settings.set_string('selected-id', next.id);
        this.arm(true);
    }
    arm(reset) {
        if (this.timer) GLib.source_remove(this.timer); this.timer = 0;
        if (this.dead || this.suspended) return;
        if (!this.settings.get_boolean('rotation-enabled') || this.eligible().length < 2) {
            this.settings.set_double('rotation-next-at', 0); return;
        }
        const now = Date.now()/1000;
        let deadline = this.settings.get_double('rotation-next-at');
        if (reset || !deadline) {deadline = now + this.settings.get_int('rotation-interval')*60; this.settings.set_double('rotation-next-at', deadline);}
        this.timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, Math.max(1, Math.ceil(deadline-now)), () => {
            this.timer = 0; this.next(); return GLib.SOURCE_REMOVE;
        });
    }
    suspend(active) {this.suspended = active; this.arm(false);}
    destroy() {
        this.dead = true;
        this.dbus?.unexport();
        if (this.timer) GLib.source_remove(this.timer); this.timer = 0;
        this.runtimeCapture.cancel(); this.cancelCapture(); this.clearWatchdog();
        this.settings.set_string('runtime-status', JSON.stringify({version:12,active:false,state:'disabled'}));
    }
}
