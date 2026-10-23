from pathlib import Path
import os,shutil,subprocess,json,signal
r=Path(__file__).resolve().parents[2];t=r/'runtime/static-overview-test';out=r/'reports/static-overview';out.mkdir(parents=True,exist_ok=True)
for name in ['data','config','cache','state','run']:(t/name).mkdir(parents=True,exist_ok=True)
(t/'run').chmod(0o700);folder=t/'data/gnome-shell/extensions';folder.mkdir(parents=True,exist_ok=True)
for name in ['wallpaperengine@waylandwe','blur-my-shell@aunetx','dash-to-dock@micxgx.gmail.com']:
 source=r/'gnome/extension' if name=='wallpaperengine@waylandwe' else Path.home()/'.local/share/gnome-shell/extensions'/name
 dest=folder/name;shutil.copytree(source,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__'))
ext=folder/'wallpaperengine@waylandwe';shutil.copy2(r/'integration/tests/static-overview-driver.js',ext/'staticOverviewTest.js')
p=ext/'wallpaperExtension.js';s=p.read_text()+"\nimport {startTest} from './staticOverviewTest.js';\n";s=s.replace('        this._manager.start();','        this._manager.start();\n        GLib.idle_add(GLib.PRIORITY_DEFAULT,()=>{startTest(this);return GLib.SOURCE_REMOVE;});');p.write_text(s)
subprocess.run(['glib-compile-schemas',str(ext/'schemas')],check=True)
for name in ['blur-my-shell','dash-to-dock']:
 (t/(name+'.ini')).write_bytes(subprocess.check_output(['dconf','dump','/org/gnome/shell/extensions/'+name+'/']))
script='''dconf load /org/gnome/shell/extensions/blur-my-shell/ < "$TEST_PROFILE/blur-my-shell.ini"
dconf load /org/gnome/shell/extensions/dash-to-dock/ < "$TEST_PROFILE/dash-to-dock.ini"
s=org.gnome.shell.extensions.wallpaperengine
gsettings reset-recursively "$s"
gsettings set "$s" library-root "$WALLPAPER_TEST_ROOT/wallpapers"
gsettings set "$s" selected-id "$WALLPAPER_TEST_REFERENCE"
gsettings set "$s" assets-path "$WALLPAPER_TEST_ROOT/assets"
gsettings set "$s" wallpaperengine-path "$WALLPAPER_TEST_ROOT/renderer/scripts/run.sh"
gsettings set org.gnome.shell enabled-extensions '["dash-to-dock@micxgx.gmail.com", "blur-my-shell@aunetx", "wallpaperengine@waylandwe"]'
gsettings set org.gnome.shell disable-user-extensions false
gsettings set org.gnome.shell welcome-dialog-last-shown-version '48.0'
exec gnome-shell --headless --virtual-monitor=1280x720 --wayland --wayland-display static-overview-test --no-x11 --sm-disable
'''
env=os.environ.copy();env.pop('DISPLAY',None);env.pop('WAYLAND_SOCKET',None)
for key,name in [('XDG_RUNTIME_DIR','run'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state')]:env[key]=str(t/name)
env.update(WALLPAPER_TEST_ROOT=str(r),TEST_PROFILE=str(t),GSETTINGS_SCHEMA_DIR=str(ext/'schemas'),GIO_USE_VFS='local',GVFS_DISABLE_FUSE='1')
before=subprocess.check_output(['dconf','dump','/org/gnome/'])
with (out/'integration.log').open('w') as log:
 p=subprocess.Popen(['dbus-run-session','--','bash','-ec',script],env=env,stdout=log,stderr=log,start_new_session=True)
 try:p.wait(timeout=75)
 finally:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
text=(out/'integration.log').read_text()
assert 'STATIC-OVERVIEW PASS' in text and 'STATIC-OVERVIEW ERROR' not in text,text[-4500:]
assert before==subprocess.check_output(['dconf','dump','/org/gnome/']),'Actual desktop settings changed'
print('PASS: static apps, image switch, dynamic handover, repeated open/close, disable; actual desktop unchanged')
