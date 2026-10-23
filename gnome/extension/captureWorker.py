#!/usr/bin/env python3
"""One-shot capture on a private Wayland compositor; never changes desktop settings.
Scene: real 4K raster targets -> filtered 1080p. Video: native decoded pixels -> 1080p.
SIGTERM, timeout and normal exit all reap the renderer and the private session.
"""
import argparse,ctypes,fcntl,json,os,pathlib,shutil,signal,subprocess,tempfile,time
import gi
gi.require_version('GdkPixbuf','2.0')
from gi.repository import GdkPixbuf,GLib

class Cancelled(Exception): pass

def terminate(proc):
    if proc is None:return
    try:os.killpg(proc.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:proc.wait(timeout=3)
    except subprocess.TimeoutExpired:pass
    # Reap any compositor helper left in its private process group as well.
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    proc.wait(timeout=3)

def capture(args):
    scene=pathlib.Path(args.scene).resolve(); output=pathlib.Path(args.output).absolute()
    project=json.loads((scene/'project.json').read_text())
    if str(project.get('type','')).lower() not in ('scene','video'):raise ValueError('Only scene/video wallpapers are supported')
    output.parent.mkdir(parents=True,exist_ok=True)
    diagnostic=pathlib.Path(args.diagnostics).absolute() if args.diagnostics else None
    if diagnostic:diagnostic.mkdir(parents=True,exist_ok=True)
    data=pathlib.Path(os.environ.get('XDG_DATA_HOME',str(pathlib.Path.home()/'.local/share')))/'gnome-wallpaper'
    data.mkdir(parents=True,exist_ok=True,mode=0o700)
    resource_lock=(data/'.write.lock').open('a')
    fcntl.flock(resource_lock,fcntl.LOCK_SH)
    lockdir=data
    # Serialize capture jobs, including quick wallpaper switches.
    with (lockdir/('wallpaper-hq-'+str(os.getuid())+'.lock')).open('a') as lock:
        deadline=time.monotonic()+65
        while True:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if time.monotonic()>deadline:raise TimeoutError('Another screenshot is still running')
                time.sleep(.1)
        with tempfile.TemporaryDirectory(prefix='wallpaper-hq-') as directory:
            root=pathlib.Path(directory)
            for name in ('run','config','data','cache','state'):(root/name).mkdir(mode=0o700)
            env={k:v for k,v in os.environ.items() if not k.startswith(('LWE_','GSETTINGS_'))}
            for name in ('DISPLAY','WAYLAND_DISPLAY','WAYLAND_SOCKET','DBUS_SESSION_BUS_ADDRESS','LD_LIBRARY_PATH','GI_TYPELIB_PATH','XDG_SESSION_ID','SESSION_MANAGER'):env.pop(name,None)
            env.update(XDG_RUNTIME_DIR=str(root/'run'),XDG_CONFIG_HOME=str(root/'config'),XDG_DATA_HOME=str(root/'data'),XDG_CACHE_HOME=str(root/'cache'),XDG_STATE_HOME=str(root/'state'),CAPTURE_PROFILE=str(root),GSETTINGS_BACKEND='memory',GIO_USE_VFS='local',GVFS_DISABLE_FUSE='1')
            script='''printf '%s' "$DBUS_SESSION_BUS_ADDRESS" > "$CAPTURE_PROFILE/bus"
exec gnome-shell --headless --virtual-monitor=1920x1080 --wayland --wayland-display wallpaper-capture --no-x11 --sm-disable
'''
            if args.quality=='standard':script=script.replace('1920x1080','2560x1440')
            shell=renderer=None;start=time.monotonic()
            try:
                with (root/'shell.log').open('w') as log:
                    shell=subprocess.Popen(['dbus-run-session','--','bash','-ec',script],env=env,stdout=log,stderr=log,start_new_session=True)
                for _ in range(200):
                    if (root/'run/wallpaper-capture').exists() and (root/'bus').exists():
                        probe=subprocess.run(['gdbus','call','--address',(root/'bus').read_text(),'--dest','org.gnome.Shell','--object-path','/org/gnome/Shell','--method','org.freedesktop.DBus.Peer.Ping'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2)
                        if probe.returncode==0:break
                    if shell.poll() is not None:raise RuntimeError('Private screenshot compositor failed')
                    time.sleep(.1)
                else:raise TimeoutError('Private screenshot compositor startup timed out')
                env.update(WAYLAND_DISPLAY='wallpaper-capture',DBUS_SESSION_BUS_ADDRESS=(root/'bus').read_text())
                if diagnostic:env['LWE_SCREENSHOT_REFERENCE']='1'
                target=root/'capture.png'
                argv=[str(pathlib.Path(args.renderer).resolve()),'--window','0x0x1920x1080','--fps','15','--silent','--disable-mouse','--disable-parallax','--no-audioreactive','--no-fullscreen-pause','--scaling',args.scaling,'--screenshot',str(target),'--screenshot-delay','45','--assets-dir',str(pathlib.Path(args.assets).resolve())]
                if args.quality=='high':argv+=['--screenshot-hq','--texturedetail','full']
                if args.freeze:argv+=['--speed','0']
                argv.append(str(scene))
                with (root/'renderer.log').open('w') as log:
                    renderer=subprocess.Popen(argv,env=env,stdout=log,stderr=log,start_new_session=True)
                last=0
                for _ in range(450):
                    if target.exists():
                        size=target.stat().st_size
                        if size>1000 and size==last:
                            try:
                                image=GdkPixbuf.Pixbuf.new_from_file(str(target))
                                if (image.get_width(),image.get_height())!=(1920,1080):raise ValueError('Unexpected screenshot dimensions')
                                break
                            except GLib.Error:pass
                        last=size
                    if renderer.poll() is not None:raise RuntimeError('Screenshot renderer exited early')
                    time.sleep(.2)
                else:raise TimeoutError('High-quality screenshot timed out')
                if args.quality=='high' and str(project['type']).lower()=='scene':
                    if 'LWE-CAPTURE-HQ' not in (root/'renderer.log').read_text(errors='replace'):
                        raise RuntimeError('Renderer does not support high-quality screenshots; update the runtime')
                # No output is exposed until renderer exit and full PNG decoding.
                terminate(renderer);renderer=None
                fd,tmp=tempfile.mkstemp(prefix='.'+output.name+'.',dir=output.parent);os.close(fd)
                try:shutil.copyfile(target,tmp);os.replace(tmp,output)
                finally:pathlib.Path(tmp).unlink(missing_ok=True)
                return {'quality':args.quality,'type':project['type'],'output':str(output),'size':[1920,1080],'elapsed':round(time.monotonic()-start,2)}
            finally:
                # Ignore repeated cancellation while cleaning up our own children.
                signal.signal(signal.SIGTERM,signal.SIG_IGN)
                signal.signal(signal.SIGINT,signal.SIG_IGN)
                terminate(renderer);terminate(shell)
                if diagnostic:
                    for p in root.iterdir():
                        if p.is_file() and p.name!='bus':shutil.copy2(p,diagnostic/p.name)
                    metadata=diagnostic/'capture.png.reference.json'
                    if metadata.exists():
                        data=json.loads(metadata.read_text())
                        for item in data['captures']:item['source']=str(diagnostic/pathlib.Path(item['source']).name)
                        metadata.write_text(json.dumps(data,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('renderer','assets','scene','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--scaling',choices=['fill','fit','stretch','default'],default='fill')
    p.add_argument('--quality',choices=['high','standard'],default='high')
    p.add_argument('--diagnostics');p.add_argument('--freeze',action='store_true')
    args=p.parse_args()
    def cancelled(_signal,_frame):raise Cancelled('Screenshot cancelled')
    signal.signal(signal.SIGTERM,cancelled);signal.signal(signal.SIGINT,cancelled)
    # If Shell dies unexpectedly, still clean up the private child session.
    parent=os.getppid();ctypes.CDLL(None).prctl(1,signal.SIGTERM)
    if os.getppid()!=parent:raise Cancelled('Parent exited')
    try:print(json.dumps(capture(args)),flush=True)
    except Exception as e:print(json.dumps({'error':str(e)}),flush=True);raise SystemExit(1)
if __name__=='__main__':main()
