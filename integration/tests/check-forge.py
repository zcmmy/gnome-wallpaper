from pathlib import Path
import os,shutil,subprocess,signal,sys,tempfile
r=Path(__file__).resolve().parents[2];label=sys.argv[1] if len(sys.argv)>1 else 'fixed';t=Path(tempfile.mkdtemp(prefix='wallpaper-forge-'));bundle=Path(os.environ.get('WALLPAPER_TEST_RUNTIME',r.parent/'wallpaper-runtime'));before=subprocess.check_output(['dconf','dump','/org/gnome/']);out=r/'reports/forge'/label;out.mkdir(parents=True,exist_ok=True)
for n in ['data','config','cache','state','run']:(t/n).mkdir(parents=True,exist_ok=True)
(t/'run').chmod(0o700);folder=t/'data/gnome-shell/extensions';folder.mkdir(parents=True,exist_ok=True)
for n in ['wallpaperengine@waylandwe','forge@jmmaranan.com','blur-my-shell@aunetx','dash-to-dock@micxgx.gmail.com','rounded-windows@marcosgt.github.io']:
 src=r/'gnome/extension' if n.startswith('wallpaper') else Path.home()/'.local/share/gnome-shell/extensions'/n
 shutil.copytree(src,folder/n,dirs_exist_ok=True)
ext=folder/'wallpaperengine@waylandwe';shutil.copy2(r/'integration/tests/forge-driver.js',ext/'testDriver.js')
p=ext/'wallpaperExtension.js';original=subprocess.check_output(['git','show',os.environ.get('FORGE_BASELINE_REF','386b092')+':gnome/extension/wallpaperExtension.js'],cwd=r).decode() if label in ['baseline','hot-update'] else p.read_text();s=original+"\nimport {startTest} from './testDriver.js';\n";s=s.replace('        this._manager.start();','        this._manager.start();\n        if(!globalThis.__forgeTestStarted){globalThis.__forgeTestStarted=true;GLib.idle_add(0,()=>{startTest(this);return false;});}');p.write_text(s)
if label=='hot-update':
 subprocess.run(['python3',str(r/'gnome/scripts/stage-forge-update.py'),str(r/'gnome/extension'),str(ext/'forgeFix')],check=True)
 (ext/'applyForgeTest.js').write_text((r/'gnome/scripts/apply-forge-fix.js').read_text().replace('../../runtime/forge-fix-live/wallpaperExtension.js','./forgeFix/wallpaperExtension.js'))
subprocess.run(['glib-compile-schemas',str(ext/'schemas')],check=True)
(t/'app.py').write_text("import gi\ngi.require_version('Gtk','3.0')\nfrom gi.repository import Gtk\nw=Gtk.Window(title='Forge regression app');w.set_default_size(600,400);w.add(Gtk.Label(label='APPLICATION MUST STAY ABOVE WALLPAPER'));w.connect('destroy',Gtk.main_quit);w.show_all();Gtk.main()\n")
env={k:v for k,v in os.environ.items() if not k.startswith(('LWE_','GSETTINGS_'))}
for k in ['DISPLAY','WAYLAND_DISPLAY','WAYLAND_SOCKET','DBUS_SESSION_BUS_ADDRESS','GI_TYPELIB_PATH','LD_LIBRARY_PATH']:env.pop(k,None)
for k,n in [('XDG_RUNTIME_DIR','run'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state')]:env[k]=str(t/n)
env.update(TEST_CASE=label,WALLPAPER_BUNDLE=str(bundle),GDK_BACKEND='wayland',TEST_PROFILE=str(t),TEST_OUT=str(out),GSETTINGS_SCHEMA_DIR=str(ext/'schemas'),GIO_USE_VFS='local',GVFS_DISABLE_FUSE='1')
for name in ['forge','blur-my-shell','dash-to-dock','rounded-windows']:
 (t/(name+'.ini')).write_bytes(subprocess.check_output(['dconf','dump','/org/gnome/shell/extensions/'+name+'/']))
script='''for name in forge blur-my-shell dash-to-dock rounded-windows; do
 dconf load /org/gnome/shell/extensions/$name/ < "$TEST_PROFILE/$name.ini"
done
s=org.gnome.shell.extensions.wallpaperengine
gsettings set "$s" library-root "$WALLPAPER_BUNDLE/wallpapers"
gsettings set "$s" selected-id '2835142671'
gsettings set "$s" assets-path "$WALLPAPER_BUNDLE/assets"
gsettings set "$s" wallpaperengine-path "$WALLPAPER_BUNDLE/bin/renderer"
gsettings set "$s" enabled false
gsettings set org.gnome.shell enabled-extensions '["blur-my-shell@aunetx", "dash-to-dock@micxgx.gmail.com", "rounded-windows@marcosgt.github.io", "forge@jmmaranan.com", "wallpaperengine@waylandwe"]'
if [ "$TEST_CASE" = late-forge ]; then
 gsettings set org.gnome.shell enabled-extensions '["blur-my-shell@aunetx", "dash-to-dock@micxgx.gmail.com", "rounded-windows@marcosgt.github.io", "wallpaperengine@waylandwe"]'
fi
gsettings set org.gnome.shell disable-user-extensions false
gsettings set org.gnome.shell welcome-dialog-last-shown-version '48.0'
exec gnome-shell --headless --virtual-monitor=1280x720 --wayland --wayland-display forge-test --no-x11 --sm-disable
'''
with (out/'integration.log').open('w') as log:
 p=subprocess.Popen(['dbus-run-session','--','bash','-ec',script],env=env,stdout=log,stderr=log,start_new_session=True)
 try:p.wait(timeout=65)
 finally:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
assert before==subprocess.check_output(['dconf','dump','/org/gnome/']),'Actual desktop settings changed'
log=(out/'integration.log').read_text()
assert 'FORGE-TEST PASS' in log and 'FORGE-TEST ERROR' not in log,log[-5000:]
shutil.rmtree(t)
print('PASS:',label,'actual desktop unchanged;',out)
