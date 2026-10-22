#!/usr/bin/env python3
"""Install and exercise the full package with old source/runtime paths hidden."""
from pathlib import Path
import os,shutil,subprocess,signal,sys,tempfile,json
r=Path(__file__).resolve().parents[1];label='package';t=Path(tempfile.mkdtemp(prefix='wallpaper-package-test-'));bundle=Path(os.environ.get('WALLPAPER_TEST_RUNTIME',r.parent/'wallpaper-runtime'));before=subprocess.check_output(['dconf','dump','/org/gnome/']);out=r/'reports/package-desktop'/t.name;out.mkdir(parents=True,exist_ok=True)
for n in ['data','config','cache','state','run','home']:(t/n).mkdir(parents=True,exist_ok=True)
(t/'run').chmod(0o700);folder=t/'data/gnome-shell/extensions';folder.mkdir(parents=True,exist_ok=True)
for n in ['wallpaperengine@waylandwe','forge@jmmaranan.com','blur-my-shell@aunetx','dash-to-dock@micxgx.gmail.com','rounded-windows@marcosgt.github.io']:
 if n.startswith('wallpaper'):
  import importlib.util
  spec=importlib.util.spec_from_file_location('installer',r/'packaging/install.py');installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
  installer.install(Path(sys.argv[1]),folder/n,False)
 else:shutil.copytree(Path.home()/'.local/share/gnome-shell/extensions'/n,folder/n,dirs_exist_ok=True)
ext=folder/'wallpaperengine@waylandwe';shutil.copy2(r/'packaging/ui-driver.js',ext/'uiTest.js');shutil.copy2(r/'packaging/desktop-driver.js',ext/'testDriver.js')
p=ext/'wallpaperExtension.js';s=p.read_text()+"\nimport {startTest} from './testDriver.js';\n";s=s.replace('        this._manager.start();','        this._manager.start();\n        if(!globalThis.__packageTestStarted){globalThis.__packageTestStarted=true;GLib.idle_add(0,()=>{startTest(this);return false;});}');p.write_text(s)
subprocess.run(['glib-compile-schemas',str(ext/'schemas')],check=True)
(t/'app.py').write_text("import gi,signal\ngi.require_version('Gtk','3.0')\nfrom gi.repository import Gtk,GLib\nw=Gtk.Window(title='Empty workspace regression app');w.set_default_size(600,400);w.add(Gtk.Label(label='APPLICATION CONTENT'));w.connect('destroy',Gtk.main_quit);w.show_all()\nsignal.signal(signal.SIGUSR1,lambda *_:GLib.idle_add(w.fullscreen));signal.signal(signal.SIGUSR2,lambda *_:GLib.idle_add(w.unfullscreen))\nGtk.main()\n")
video='--video' in sys.argv[2:]
if video:
 scene='合成 视频';fixture=t/'fixtures'/scene
 subprocess.run(['/usr/bin/python3',str(r/'packaging/video-fixture.py'),str(fixture)],check=True)
else:scene=os.environ.get('WALLPAPER_TEST_ID')
if not scene:
 for path in sorted((bundle/'wallpapers').iterdir()):
  try:
   project=json.loads((path/'project.json').read_text())
   if project.get('type')=='scene' and (path/'static-background.png').exists():scene=path.name;break
  except (OSError,ValueError):pass
if not scene:raise SystemExit('Provide a runtime with a scene and static image, or set WALLPAPER_TEST_ID')

env={k:v for k,v in os.environ.items() if not k.startswith(('LWE_','GSETTINGS_'))}
for k in ['DISPLAY','WAYLAND_DISPLAY','WAYLAND_SOCKET','DBUS_SESSION_BUS_ADDRESS','GI_TYPELIB_PATH','LD_LIBRARY_PATH']:env.pop(k,None)
for k,n in [('XDG_RUNTIME_DIR','run'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state')]:env[k]=str(t/n)
(t/'output').mkdir()
env.update(HOME=str(t/'home'),XDG_SESSION_TYPE='wayland',TEST_SCENE=scene,TEST_CASE=label,WALLPAPER_BUNDLE=str(bundle),GDK_BACKEND='wayland',TEST_PROFILE=str(t),TEST_OUT=str(t/'output'),GSETTINGS_SCHEMA_DIR=str(ext/'schemas'),GIO_USE_VFS='local',GVFS_DISABLE_FUSE='1')
data=t/'data/gnome-wallpaper'
for request in [{'operation':'assets','assets':str(bundle/'assets')},{'operation':'import','source':str(fixture if video else bundle/'wallpapers'/scene)}]:
 with (out/'import.log').open('a') as log:
  subprocess.run(['/usr/bin/python3',str(ext/'helpers/dataWorker.py'),'--root',str(data)],input=json.dumps(request),text=True,env=env,stdout=log,check=True)
for name in ['forge','blur-my-shell','dash-to-dock','rounded-windows']:
 (t/(name+'.ini')).write_bytes(subprocess.check_output(['dconf','dump','/org/gnome/shell/extensions/'+name+'/']))
script='''for name in forge blur-my-shell dash-to-dock rounded-windows; do
 dconf load /org/gnome/shell/extensions/$name/ < "$TEST_PROFILE/$name.ini"
done
s=org.gnome.shell.extensions.wallpaperengine
gsettings set "$s" library-root "$XDG_DATA_HOME/gnome-wallpaper/wallpapers"
gsettings set "$s" selected-id "$TEST_SCENE"
gsettings set "$s" assets-path "$XDG_DATA_HOME/gnome-wallpaper/assets"
gsettings set "$s" wallpaperengine-path "$XDG_DATA_HOME/gnome-shell/extensions/wallpaperengine@waylandwe/backend/linux-x86_64/bin/renderer"
gsettings set "$s" enabled false
gsettings set org.gnome.shell enabled-extensions '["blur-my-shell@aunetx", "dash-to-dock@micxgx.gmail.com", "rounded-windows@marcosgt.github.io", "forge@jmmaranan.com", "wallpaperengine@waylandwe"]'
gsettings set org.gnome.shell disable-user-extensions false
gsettings set org.gnome.shell welcome-dialog-last-shown-version '48.0'
exec gnome-shell --headless --virtual-monitor=1280x720 --wayland --wayland-display forge-test --no-x11 --sm-disable
'''
with (out/'integration.log').open('w') as log:
 hidden=[r,r.parent/'wallpaper_adapter',r.parent/'wallpaper-runtime',r.parent/'wallpaper-unicode-fix',r.parent/'wallpaper-attention-fix']
 sandbox=['bwrap','--ro-bind','/','/','--bind','/tmp','/tmp','--dev-bind','/dev','/dev','--proc','/proc']
 sandbox+=['--ro-bind',str(ext),str(ext)]
 for path in hidden:
  if path.exists():sandbox+=['--tmpfs',str(path)]
 p=subprocess.Popen(sandbox+['dbus-run-session','--','bash','-ec',script],env=env,stdout=log,stderr=log,start_new_session=True)
 try:p.wait(timeout=230)
 finally:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
assert before==subprocess.check_output(['dconf','dump','/org/gnome/']),'Actual desktop settings changed'
log=(out/'integration.log').read_text()
assert 'PACKAGE-TEST PASS' in log and 'PACKAGE-TEST ERROR' not in log,log[-5000:]
shutil.copytree(t/'output',out,dirs_exist_ok=True)
shutil.rmtree(t)
print('PASS:',label,'actual desktop unchanged;',out)
