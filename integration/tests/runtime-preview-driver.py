from pathlib import Path
import os,subprocess,socket,time,json
r=Path(os.environ['WALLPAPER_BUNDLE']);t=Path(os.environ['RUNTIME_TEST_DIR']);sock=t/'preview.sock'
env=os.environ.copy();env['LWE_SOCKET']=str(sock)
for key,sub in [('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state')]:
 path=t/'preview-state'/sub;path.mkdir(parents=True,exist_ok=True);env[key]=str(path)
def api(cmd,args={}):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(2);s.connect(str(sock));s.sendall((json.dumps({'id':1,'cmd':cmd,'args':args})+'\n').encode());data=b''
  while b'\n' not in data:
   chunk=s.recv(65536)
   if not chunk:raise RuntimeError('socket closed')
   data+=chunk
  return json.loads(data)
result={}
with (t/'reports/standalone-preview.log').open('w') as f:
 p=subprocess.Popen([str(r/'bin/preview'),'--listen','--screenshot',str(t/'reports/standalone-preview.png')],env=env,stdout=f,stderr=subprocess.STDOUT)
 try:
  for _ in range(150):
   assert p.poll() is None,'preview exited early'
   try:
    result['before']=api('status')['result'];break
   except (OSError,ValueError):time.sleep(.1)
  assert result,'socket did not start'
  assert api('pointer',{'x':.2,'y':.8,'left':False,'right':False,'active':True})['ok']
  time.sleep(.1);pointer=api('status')['result']['pointer'];assert pointer['active'] and abs(pointer['x']-.2)<.001
  time.sleep(4);result['after']=api('status')['result'];assert result['after']['frames']>result['before']['frames']+30
  assert result['after']['audio_processing'] and result['after']['parallax'] and result['after']['particles']
  maps=Path('/proc',str(p.pid),'maps').read_text();assert os.environ['WALLPAPER_DEVELOPMENT_ROOT']+'/' not in maps
  assert str(Path('/proc',str(p.pid),'exe').resolve()).startswith(str(r))
  assert (t/'reports/standalone-preview.png').stat().st_size>10000
  result['pointer']=pointer;result['no_development_dependencies']=True
 finally:
  p.terminate()
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:p.kill();p.wait()
(t/'reports/standalone-preview.json').write_text(json.dumps(result,indent=2))
print('PASS: relocated standalone preview, animation frames, pointer IPC, audio enabled, screenshot, no development paths')
