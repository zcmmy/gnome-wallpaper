#!/usr/bin/env python3
"""Test old cached Shell modules -> installed full package without restarting Shell."""
import importlib.util,json,os,pathlib,shutil,signal,subprocess,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1]
archive=pathlib.Path(sys.argv[1]).resolve()
t=pathlib.Path(tempfile.mkdtemp(prefix='wp-update-'))
out=root/'reports/session-update';out.mkdir(parents=True,exist_ok=True)
for name in ['data','config','cache','state','run','home']:(t/name).mkdir(mode=0o700)
ext=t/'data/gnome-shell/extensions/wallpaperengine@waylandwe'
old=pathlib.Path(os.environ.get('WALLPAPER_OLD_EXTENSION',str(pathlib.Path.home()/'.local/share/gnome-shell/extensions/wallpaperengine@waylandwe')))
shutil.copytree(old,ext)
for name in ['forge@jmmaranan.com','blur-my-shell@aunetx','dash-to-dock@micxgx.gmail.com']:
 shutil.copytree(pathlib.Path.home()/'.local/share/gnome-shell/extensions'/name,ext.parent/name)
bundle=pathlib.Path(os.environ.get('WALLPAPER_TEST_RUNTIME',str(root.parent/'wallpaper-runtime')))
scene=next(p for p in sorted((bundle/'wallpapers').iterdir()) if (p/'static-background.png').is_file() and json.loads((p/'project.json').read_text()).get('type')=='scene')
data=t/'data/gnome-wallpaper'
for request in [{'operation':'assets','assets':str(bundle/'assets')},{'operation':'import','source':str(scene)}]:
 subprocess.run(['/usr/bin/python3',str(root/'gnome/extension/helpers/dataWorker.py'),'--root',str(data)],input=json.dumps(request),text=True,stdout=subprocess.DEVNULL,check=True)
shutil.copy2(root/'packaging/session-update-driver.js',ext/'sessionTest.js')
p=ext/'wallpaperExtension.js';s=p.read_text()+"\nimport {runSessionTest} from './sessionTest.js';\n";s=s.replace('        this._manager.start();','        this._manager.start();\n        GLib.idle_add(0,()=>{runSessionTest(this);return false;});');p.write_text(s)
subprocess.run(['glib-compile-schemas',str(ext/'schemas')],check=True)
env={k:v for k,v in os.environ.items() if k not in ['DISPLAY','WAYLAND_DISPLAY','WAYLAND_SOCKET','DBUS_SESSION_BUS_ADDRESS','GSETTINGS_BACKEND','LD_LIBRARY_PATH']}
for key,name in [('RUNTIME','run'),('DATA','data'),('CONFIG','config'),('CACHE','cache'),('STATE','state')]:env['XDG_'+key+('_DIR' if key=='RUNTIME' else '_HOME')]=str(t/name)
env.update(HOME=str(t/'home'),XDG_SESSION_TYPE='wayland',GSETTINGS_SCHEMA_DIR=str(ext/'schemas'),GIO_USE_VFS='local',GVFS_DISABLE_FUSE='1',TEST_SOURCE=str(root),TEST_ARCHIVE=str(archive),TEST_SCENE=scene.name,GDK_BACKEND='wayland')
script='''s=org.gnome.shell.extensions.wallpaperengine
gsettings set "$s" library-root "$XDG_DATA_HOME/gnome-wallpaper/wallpapers"
gsettings set "$s" selected-id "$TEST_SCENE"
gsettings set "$s" fps 15
gsettings set "$s" enabled false
gsettings set org.gnome.shell enabled-extensions '["forge@jmmaranan.com", "blur-my-shell@aunetx", "dash-to-dock@micxgx.gmail.com", "wallpaperengine@waylandwe"]'
gsettings set org.gnome.shell welcome-dialog-last-shown-version '48.0'
exec gnome-shell --headless --virtual-monitor=1280x720 --wayland --wayland-display package-session-test --no-x11 --sm-disable
'''
before=subprocess.check_output(['dconf','dump','/org/gnome/'])
with (out/'integration.log').open('w') as log:
 p=subprocess.Popen(['dbus-run-session','--','bash','-ec',script],env=env,stdout=log,stderr=log,start_new_session=True)
 try:p.wait(timeout=100)
 finally:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
assert before==subprocess.check_output(['dconf','dump','/org/gnome/']),'Desktop settings changed'
log=(out/'integration.log').read_text();assert 'SESSION-UPDATE PASS' in log and 'SESSION-UPDATE ERROR' not in log,log[-5000:]
shutil.rmtree(t);print('PASS: cached old modules, atomic install, explicit session update, dynamic playback and repeat apply')
