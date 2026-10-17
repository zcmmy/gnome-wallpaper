#!/usr/bin/env python3
from gi.repository import Gio,GLib
from pathlib import Path
import json,socket,time,subprocess
r=Path(__file__).resolve().parents[2];b=Gio.bus_get_sync(Gio.BusType.SESSION,None)
def desktop():
 return json.loads(b.call_sync('org.gnome.Shell','/org/gnome/Shell/WallpaperAdapterTrial','org.wallpaper.Adapter.Trial','Snapshot',None,GLib.VariantType('(s)'),Gio.DBusCallFlags.NONE,5000,None).unpack()[0])
def api(cmd,args=None):
 path=desktop()['renderer']['socket']
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(4);s.connect(path);s.sendall((json.dumps({'id':1,'cmd':cmd,'args':args or {}})+'\n').encode());data=b''
  while b'\n' not in data:
   chunk=s.recv(65536)
   if not chunk:raise RuntimeError('closed')
   data+=chunk
  result=json.loads(data)
  assert result['ok'],result
  return result['result']
def measure(tag,seconds):
 subprocess.run(['/usr/bin/python3',str(r/'integration/scripts/measure-desktop.py'),tag,'--seconds',str(seconds)],check=True)
schema=Gio.SettingsSchemaSource.new_from_directory(str(r/'gnome/extension/schemas'),Gio.SettingsSchemaSource.get_default(),False).lookup('org.gnome.shell.extensions.wallpaperengine',False)
settings=Gio.Settings.new_full(schema,None,None)
original=api('status');original_path=settings.get_string('wallpaperengine-path')
(r/'reports/perf-original-status.json').write_text(json.dumps(original,indent=2))
def switch(path):
 old=desktop()['renderer']['pid'];settings.set_string('wallpaperengine-path',path);Gio.Settings.sync()
 for _ in range(100):
  time.sleep(.2);state=desktop()
  if state['renderer']['pid'] and state['renderer']['pid']!=old and state['renderer']['adopted']:
   try:
    status=api('status')
    if status['frames']>30:break
   except (OSError,KeyError):pass
 else:raise RuntimeError('Renderer restart did not complete')
 time.sleep(3)
try:
 print('PHASE paused',flush=True);api('pause');time.sleep(2);measure('paused',12)
 api('resume');time.sleep(3)
 print('PHASE fps24',flush=True);api('set-fps',{'fps':24});time.sleep(3);measure('fps24',25)
 api('set-fps',{'fps':original['fps']});time.sleep(3)
 print('PHASE baseline repeat',flush=True);measure('baseline-repeat',25)
 print('PHASE effect buffers 85 percent',flush=True);switch(str(r/'integration/scripts/renderer-quality-probe.sh'));measure('effect85',30)
finally:
 if settings.get_string('wallpaperengine-path')!=original_path:
  print('RESTORE original launcher',flush=True);switch(original_path)
 api('set-fps',{'fps':original['fps']});api('pause' if original['manual_pause'] else 'resume')
 print('RESTORED',flush=True)
measure('restored30',25)
