#!/usr/bin/env python3
import json, socket, time, pathlib, subprocess, os, signal
r=pathlib.Path(__file__).resolve().parents[2]
log=r/'logs'/os.environ.get('WALLPAPER_TEST_LOG','gnome-integration-final.log'); out=[]; start=time.monotonic()
with log.open('w') as f:
 proc=subprocess.Popen([str(r/'integration/tests'/os.environ.get('WALLPAPER_TEST_LAUNCHER','nested-gnome.sh'))],cwd=r,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 try:
  while proc.poll() is None and time.monotonic()-start<85:
   text=log.read_text(errors='replace')
   entries=[json.loads(x.split('WALLPAPER-TEST ',1)[1]) for x in text.splitlines() if 'WALLPAPER-TEST {' in x]
   if entries:
    try:
     with socket.socket(socket.AF_UNIX) as s:
      s.settimeout(.35); s.connect(entries[-1]['socket']);s.sendall(b'{"id":1,"cmd":"status"}\n'); data=b''
      while b'\n' not in data:
       chunk=s.recv(65536)
       if not chunk:break
       data+=chunk
      j=json.loads(data)['result']; out.append({'t':round(time.monotonic()-start,2),'phase':entries[-1]['label'],'pid':j['pid'],'frames':j['frames'],'pointer':j.get('pointer'),'fps':j['fps']})
    except (OSError,ValueError,KeyError):pass
   time.sleep(.5)
 finally:
  if proc.poll() is None:
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
text=log.read_text(errors='replace')
entries=[json.loads(x.split('WALLPAPER-TEST ',1)[1]) for x in text.splitlines() if 'WALLPAPER-TEST {' in x]
(r/'reports'/os.environ.get('WALLPAPER_TEST_REPORT','gnome-integration.json')).write_text(json.dumps({'snapshots':entries,'samples':out},indent=2))
by={x['label']:x for x in entries}
assert 'complete' in by,'test did not complete'
for phase in ['mapped','pointer-10','pointer-16','pointer-22','overview','apps','workspace','restarted','reenabled']:
 e=by[phase]
 assert e['adopted'] and e['skipTaskbar'] and e['sticky'] and e['parentIsBackground'] and e['visible'],(phase,e)
 assert not e['inTabList'] and not e['focused'],(phase,e)
 assert e['rect']['width']==e['monitor']['width'] and e['rect']['height']==e['monitor']['height'], (phase,e)
 assert e['paintOrigin']==[e['monitor']['x'],e['monitor']['y']],(phase,e)
assert by['restarted']['restartChangedPid']
assert not by['disabled']['adopted'] and 'pid' not in by['disabled']
for phase,pos in [('pointer-10',.1),('pointer-16',.9),('pointer-22',.5)]:
 assert any(e['phase']==phase and e['pointer']['active'] and abs(e['pointer']['x']-pos)<.002 and abs(e['pointer']['y']-pos)<.002 for e in out),phase
errors=[line for line in text.splitlines() if any(marker in line for marker in ['JS ERROR','WALLPAPER-TEST ERROR','Clutter-CRITICAL','assertion'])]
assert not errors,errors[:8]
print('PASS: GNOME 48 background ownership, Alt-Tab exclusion, focus, workspace, restart, pause/resume, disable/reenable and compositor pointer at 10/50/90%')

for phase in ['overview','apps']:
 e=by[phase]; o=e['overviewWallpaper']; b=o['backdrop']; m=e['monitor']
 assert b['mapped'] and b['x']==m['x'] and b['y']==m['y'] and b['width']==m['width'] and b['height']==m['height'],(phase,o)
 assert o['clones'] and all(c['sourceMatches'] for c in o['clones']),(phase,o)
 assert any(c['bounds']['mapped'] for c in o['clones']),(phase,o)
assert by['disabled']['overviewWallpaper']['backdrop'] is None
assert not by['disabled']['overviewWallpaper']['clones']
print('PASS: overview/app-grid full-monitor coverage, shared renderer surface and restart cleanup')

assert by['apps']['overviewState']==2,by['apps']

for c in by['apps']['overviewWallpaper']['clones']:
 b=c['bounds']; m=by['apps']['monitor']
 if b['mapped']:
  assert b['width'] < m['width'] * .4, ('preview expanded into strip',b)
  assert abs(b['width']/b['height']-m['width']/m['height']) < .05, ('distorted preview',b)
