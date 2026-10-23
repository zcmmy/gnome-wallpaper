#!/usr/bin/env python3
"""Exercise empty first-use UI and resource preparation in a private GNOME session."""
import json,os,pathlib,shutil,signal,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='wp-first-ui-') as directory:
 t=pathlib.Path(directory)
 for n in ['data','config','state','cache','run','home']:(t/n).mkdir(mode=0o700)
 schemas=t/'schemas';shutil.copytree(root/'gnome/extension/schemas',schemas)
 subprocess.run(['glib-compile-schemas',str(schemas)],check=True)
 for n in ['models','shaders','scripts']:
  p=t/'fixture/assets'/n;p.mkdir(parents=True);(p/'fixture').write_text('test')
 scene=t/'fixture/wallpaper';scene.mkdir()
 (scene/'project.json').write_text(json.dumps({'type':'scene','file':'scene.json','title':'Synthetic fixture'}));(scene/'scene.json').write_text('{}')
 ext=t/'data/gnome-shell/extensions/first-use-test@local';ext.mkdir(parents=True)
 (ext/'metadata.json').write_text(json.dumps({'uuid':ext.name,'name':'First use test','description':'Isolated test runner','shell-version':['48']}))
 (ext/'extension.js').write_text("""import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
export default class Test extends Extension {
 enable(){GLib.timeout_add(0,1500,()=>{
  const p=Gio.Subprocess.new(['gjs','-m',GLib.getenv('TEST_SCRIPT')],Gio.SubprocessFlags.NONE);
  p.wait_async(null,()=>global.context.terminate());return false;
 });}
 disable(){}
}
""")
 env={k:v for k,v in os.environ.items() if k not in ['DISPLAY','WAYLAND_DISPLAY','WAYLAND_SOCKET','DBUS_SESSION_BUS_ADDRESS','LD_LIBRARY_PATH','GSETTINGS_BACKEND']}
 for k,n in [('XDG_DATA_HOME','data'),('XDG_CONFIG_HOME','config'),('XDG_STATE_HOME','state'),('XDG_CACHE_HOME','cache'),('XDG_RUNTIME_DIR','run'),('HOME','home')]:env[k]=str(t/n)
 env.update(XDG_SESSION_TYPE='wayland',GDK_BACKEND='wayland',WAYLAND_DISPLAY='first-use-ui',GIO_USE_VFS='local',GVFS_DISABLE_FUSE='1',GSETTINGS_SCHEMA_DIR=str(schemas),TEST_FIXTURE=str(t/'fixture'),TEST_SCRIPT=str(root/'gnome/tests/check-first-use-ui.js'))
 script="gsettings set org.gnome.shell enabled-extensions '[\"first-use-test@local\"]'\ngsettings set org.gnome.shell welcome-dialog-last-shown-version '48.0'\nexec gnome-shell --headless --virtual-monitor=1280x720 --wayland --wayland-display first-use-ui --no-x11 --sm-disable"
 before=subprocess.check_output(['dconf','dump','/org/gnome/'])
 with (t/'log').open('w') as log:
  p=subprocess.Popen(['dbus-run-session','--','bash','-ec',script],env=env,stdout=log,stderr=log,start_new_session=True)
  try:p.wait(timeout=45)
  finally:
   try:os.killpg(p.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   p.wait(timeout=5)
 text=(t/'log').read_text()
 assert 'FIRST-USE-UI PASS' in text and 'FIRST-USE-UI ERROR' not in text,text[-5000:]
 assert before==subprocess.check_output(['dconf','dump','/org/gnome/']),'Actual desktop settings changed'
 print('PASS: empty first-use guidance, separate assets/library preparation, no automatic selection or playback')
