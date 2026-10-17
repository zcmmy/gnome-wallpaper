#!/usr/bin/env python3
import pathlib, socket, subprocess, os, time, json
r=pathlib.Path(__file__).resolve().parents[2]
path=str(r/'runtime/pointer-validation.sock');env=os.environ.copy();env['LWE_SOCKET']=path
result={};p=None

def api(cmd,args=None):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(1);s.connect(path);s.sendall((json.dumps({'id':1,'cmd':cmd,'args':args or {}})+'\n').encode());data=b''
  while b'\n' not in data:
   b=s.recv(65536)
   if not b:break
   data+=b
  return json.loads(data)
with (r/'logs/pointer-validation.log').open('w') as log:
 try:
  p=subprocess.Popen([str(r/'renderer/scripts/run.sh'),'--window','100x100x960x540','--fps','30','--listen','--silent','--no-fullscreen-pause','--assets-dir',str(r/'assets'),str(r/'wallpaper')],env=env,stdout=log,stderr=subprocess.STDOUT)
  for i in range(60):
   if pathlib.Path(path).exists():
    try:
     if api('status')['ok']:break
    except OSError:pass
   time.sleep(.1)
  good={'x':.1,'y':.9,'left':True,'right':False,'active':True}
  assert api('pointer',good)['ok']; time.sleep(.12)
  result['active']=api('status')['result']['pointer']; assert result['active']['active'] and result['active']['left']
  assert abs(result['active']['x']-.1)<1e-8 and abs(result['active']['y']-.9)<1e-8
  assert not api('pointer',dict(good,x=2))['ok']
  time.sleep(.65);result['expired']=api('status')['result']['pointer']
  assert not result['expired']['active'] and not result['expired']['left']
  assert api('pointer',good)['ok'];assert api('set-mouse',{'enabled':False})['ok'];time.sleep(.1)
  result['disabled']=api('status')['result']['pointer'];assert not result['disabled']['active'] and not result['disabled']['left']
  api('set-mouse',{'enabled':True})
  assert api('pointer',dict(good,active=False))['ok'];time.sleep(.1)
  result['inactive']=api('status')['result']['pointer'];assert not result['inactive']['active'] and not result['inactive']['left']
 finally:
  if p is not None and p.poll() is None:
   p.terminate()
   try:p.wait(timeout=3)
   except subprocess.TimeoutExpired:p.kill();p.wait()
(r/'reports/pointer-runtime.json').write_text(json.dumps(result,indent=2))
print('PASS: actual pointer coordinates/buttons, invalid input refusal, 500ms expiry, disable and inactive release')
