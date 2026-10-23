#!/usr/bin/env python3
"""Render screenshots in an isolated headless GNOME session; never install them."""
import ctypes,json,os,pathlib,signal,subprocess,time
import gi
gi.require_version('GdkPixbuf','2.0')
from gi.repository import GdkPixbuf,GLib
r=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(os.environ.get('WALLPAPER_CAPTURE_OUTPUT',str(r/'reports/capture-filter')));out.mkdir(parents=True,exist_ok=True)
bundle=pathlib.Path(os.environ['WALLPAPER_CAPTURE_RUNTIME']) if 'WALLPAPER_CAPTURE_RUNTIME' in os.environ else None
library=bundle/'wallpapers' if bundle else r/'wallpapers'
executable=bundle/'bin/renderer' if bundle else r/'renderer/scripts/run.sh'
assets=bundle/'assets' if bundle else r/'assets'
profile=r/'runtime/capture-test'
for name in ['run','config','data','cache','state']:(profile/name).mkdir(parents=True,exist_ok=True)
(profile/'run').chmod(0o700);(profile/'bus-address').unlink(missing_ok=True)
env=os.environ.copy()
for name in ['DISPLAY','WAYLAND_DISPLAY','WAYLAND_SOCKET','DBUS_SESSION_BUS_ADDRESS','LD_LIBRARY_PATH','GI_TYPELIB_PATH']:env.pop(name,None)
env.update(XDG_RUNTIME_DIR=str(profile/'run'),XDG_CONFIG_HOME=str(profile/'config'),XDG_DATA_HOME=str(profile/'data'),XDG_CACHE_HOME=str(profile/'cache'),XDG_STATE_HOME=str(profile/'state'),WALLPAPER_CAPTURE_PROFILE=str(profile))
script="""printf '%s' "$DBUS_SESSION_BUS_ADDRESS" > "$WALLPAPER_CAPTURE_PROFILE/bus-address"
gsettings set org.gnome.shell enabled-extensions '[]'
gsettings set org.gnome.shell disable-user-extensions true
gsettings set org.gnome.shell welcome-dialog-last-shown-version '48.0'
exec gnome-shell --headless --virtual-monitor=2560x1440 --wayland --wayland-display wallpaper-capture-test --no-x11 --sm-disable
"""
def stop(proc):
 if proc and proc.poll() is None:
  os.killpg(proc.pid,signal.SIGTERM)
  try:proc.wait(timeout=4)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
def save(pixels,width,height,path):
 pix=GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(pixels)),GdkPixbuf.Colorspace.RGB,False,8,width,height,width*3);pix.savev(str(path),'png',[],[])
def legacy_capture(file):
 metadata=json.loads(pathlib.Path(str(file)+'.reference.json').read_text());width,height=metadata['output'];bitmap=bytearray(width*height*3)
 f=lambda n:ctypes.c_float(n).value
 for c in metadata['captures']:
  pix=GdkPixbuf.Pixbuf.new_from_file(c['source']);data=pix.get_pixels();stride=pix.get_rowstride();sw,sh=c['width'],c['height'];vw,vh=c['viewport'];u0,u1,v0,v1=c['uv']
  xs=[max(0,min(sw-1,int(f(f(u0+f(f(x/vw)*f(u1-u0)))*sw))))*3 for x in range(vw)]
  ys=[max(0,min(sh-1,int(f(f(v0+f(f(y/vh)*f(v1-v0)))*sh))))*stride for y in range(vh)]
  for y,sy in enumerate(ys):
   fy=y if metadata['vflip'] else vh-y-1
   for x,sx in enumerate(xs):
    to=(fy*width+x+c['offset'])*3;bitmap[to:to+3]=data[sy+sx:sy+sx+3]
 save(bitmap,width,height,out/'roxy-before-same-frame.png')
 pix=GdkPixbuf.Pixbuf.new_from_file(str(file));assert(pix.get_width(),pix.get_height())==(1920,1080)
 # Crop matching line art and enlarge with nearest filtering only for inspection.
 for name,path in [('before',out/'roxy-before-same-frame.png'),('after',file)]:
  image=GdkPixbuf.Pixbuf.new_from_file(str(path));crop=image.new_subpixbuf(720,300,320,240).scale_simple(960,720,GdkPixbuf.InterpType.NEAREST);crop.savev(str(out/('roxy-'+name+'-detail.png')),'png',[],[])
 return metadata
shell=None;renderer=None;results=[]
try:
 with (out/'shell.log').open('w') as log:shell=subprocess.Popen(['dbus-run-session','--','bash','-ec',script],env=env,stdout=log,stderr=log,start_new_session=True)
 for _ in range(200):
  if (profile/'run/wallpaper-capture-test').exists() and (profile/'bus-address').exists():
   probe=subprocess.run(['gdbus','call','--address',(profile/'bus-address').read_text(),'--dest','org.gnome.Shell','--object-path','/org/gnome/Shell','--method','org.freedesktop.DBus.Peer.Ping'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   if probe.returncode==0:break
  if shell.poll() is not None:raise RuntimeError('Private compositor failed')
  time.sleep(.1)
 else:raise RuntimeError('Private compositor startup timed out')
 env.update(WAYLAND_DISPLAY='wallpaper-capture-test',DBUS_SESSION_BUS_ADDRESS=(profile/'bus-address').read_text())
 scenes=sorted(library.glob('*/project.json'),key=lambda p:(p.parent.name!=os.environ.get('WALLPAPER_TEST_REFERENCE',''),p.parent.name))
 if os.environ.get("WALLPAPER_CAPTURE_IDS"):scenes=[p for p in scenes if p.parent.name in os.environ["WALLPAPER_CAPTURE_IDS"].split(",")]
 assert scenes,"No matching wallpapers"
 for project in scenes:
  scene=project.parent;file=out/(scene.name+'.png');file.unlink(missing_ok=True)
  run=env.copy()
  if scene.name==os.environ.get('WALLPAPER_TEST_REFERENCE',''):run['LWE_SCREENSHOT_REFERENCE']='1'
  with (out/(scene.name+'.log')).open('w') as log:
   renderer=subprocess.Popen([str(executable),'--window','0x0x1920x1080','--fps','15','--silent','--no-audioreactive','--no-fullscreen-pause','--scaling','fill','--screenshot',str(file),'--screenshot-delay','45','--assets-dir',str(assets),str(scene)],env=run,stdout=log,stderr=log,start_new_session=True)
   last=0
   for _ in range(300):
    if file.exists():
     size=file.stat().st_size
     if size>2000 and size==last:
      pix=GdkPixbuf.Pixbuf.new_from_file(str(file));break
     last=size
    if renderer.poll() is not None:raise RuntimeError('Renderer exited: '+scene.name)
    time.sleep(.2)
   else:raise RuntimeError('Screenshot timeout: '+scene.name)
  stop(renderer);renderer=None
  assert (pix.get_width(),pix.get_height())==(1920,1080)
  result={'id':scene.name,'image':str(file),'size':[1920,1080]}
  if scene.name==os.environ.get('WALLPAPER_TEST_REFERENCE',''):result['same_frame_reference']=legacy_capture(file)
  results.append(result);print('PASS: '+scene.name+' 1920x1080 filtered screenshot',flush=True)
 (out/'summary.json').write_text(json.dumps({'passed':True,'captures':results,'live_desktop_modified':False},ensure_ascii=False,indent=2)+'\n')
finally:stop(renderer);stop(shell)
