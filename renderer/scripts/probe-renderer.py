#!/usr/bin/env python3
"""Bounded preview probe: runs one local renderer, samples its own process, then stops it."""
import argparse, json, os, pathlib, signal, socket, statistics, subprocess, time
p=argparse.ArgumentParser();p.add_argument('variant',choices=['portghost'],nargs='?',default='portghost');p.add_argument('--fps',type=int,default=30);p.add_argument('--seconds',type=int,default=20);p.add_argument('--tag');p.add_argument('--smoke',action='store_true');p.add_argument('--disable-audio',action='store_true');p.add_argument('--scene');p.add_argument('--unclamped',action='store_true');a=p.parse_args()
r=pathlib.Path(__file__).resolve().parents[2];tag=a.tag or f'{a.variant}-{a.fps}fps'
if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in tag):raise ValueError('invalid tag')
env=os.environ.copy()
for k,v in [('XDG_CACHE_HOME','cache'),('XDG_CONFIG_HOME','config'),('XDG_STATE_HOME','state')]:env[k]=str(r/'runtime'/v)
sock=str(r/'runtime'/f'{tag}.sock');env['LWE_SOCKET']=sock
shot=r/'reports'/f'{tag}.png'
if shot.exists():shot.unlink()
exe=r/'renderer/scripts/run.sh'
cmd=[str(exe),'--window','100x100x960x540','--fps',str(a.fps),'--silent','--no-fullscreen-pause','--assets-dir',str(r/'assets'),'--screenshot',str(shot)]
if a.variant=='portghost':cmd+=['--listen']
if a.unclamped and a.variant=='portghost':cmd+=['--resclamp','0','--effectclamp','0']
if a.disable_audio:cmd+=['--no-audio-processing']
cmd+=[str(pathlib.Path(a.scene).resolve() if a.scene else r/('renderer/tests/fixtures/smoke-scene' if a.smoke else 'wallpaper'))]

def api():
    try:
        with socket.socket(socket.AF_UNIX) as s:
            s.settimeout(.5);s.connect(sock);s.sendall(b'{"id":1,"cmd":"status","args":{}}\n');b=b''
            while b'\n' not in b:
                chunk=s.recv(65536)
                if not chunk:raise ValueError('socket closed')
                b+=chunk
                if len(b)>1048576:raise ValueError('oversize reply')
            return json.loads(b.split(b'\n')[0])
    except (OSError,ValueError):return None

def sample(pid):
    base=pathlib.Path('/proc')/str(pid)
    st=(base/'stat').read_text().split(') ',1)[1].split()
    d={'t':time.monotonic(),'cpu_seconds':(int(st[11])+int(st[12]))/os.sysconf('SC_CLK_TCK')}
    for line in (base/'status').read_text().splitlines():
        if line.startswith(('VmRSS:','VmHWM:')):k,v,*_=line.split();d[k[:-1]+'_kib']=int(v)
    try:
        for line in (base/'smaps_rollup').read_text().splitlines():
            if line.startswith(('Pss:','Private_Dirty:')):k,v,*_=line.split();d[k[:-1]+'_kib']=int(v)
    except OSError:pass
    clients={}
    for f in (base/'fdinfo').iterdir():
        try:
            lines=f.read_text().splitlines();vals=dict(x.split(':',1) for x in lines if ':' in x)
            if 'drm-client-id' in vals:clients[vals['drm-client-id'].strip()]={k:v.strip() for k,v in vals.items() if k.startswith('drm-')}
        except OSError:pass
    d['drm_clients']=clients
    if a.variant=='portghost':d['engine_status']=api()
    return d

out={'command':cmd,'variant':a.variant,'fps_cap':a.fps,'samples':[],'note':'960x540 independent window; CPU 100% means one core. RSS/PSS are process memory, not VRAM.'}
start=time.monotonic();proc=None
with (r/'logs'/f'run-{tag}.log').open('w') as log:
    try:
        proc=subprocess.Popen(cmd,cwd=r,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        while proc.poll() is None and time.monotonic()-start<a.seconds+15:
            if shot.exists() and 'seconds_until_screenshot' not in out:out['seconds_until_screenshot']=time.monotonic()-start
            try:out['samples'].append(sample(proc.pid))
            except (FileNotFoundError,ProcessLookupError):break
            if 'seconds_until_screenshot' in out and time.monotonic()-start>out['seconds_until_screenshot']+a.seconds:break
            time.sleep(1)
        out['running_before_stop']=proc.poll() is None
    finally:
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        out['exit_code']=proc.returncode if proc else None
out['elapsed_seconds']=time.monotonic()-start
ss=[x for x in out['samples'] if x['t']-start>out.get('seconds_until_screenshot',100000)+3]
if len(ss)>1:
    out['steady_cpu_percent_one_core']=100*(ss[-1]['cpu_seconds']-ss[0]['cpu_seconds'])/(ss[-1]['t']-ss[0]['t'])
    out['median_rss_mib']=statistics.median(x.get('VmRSS_kib',0) for x in ss)/1024
    out['median_pss_mib']=statistics.median(x.get('Pss_kib',0) for x in ss)/1024
    statuses=[(x['t'],x['engine_status']['result'].get('frames')) for x in ss if x.get('engine_status',{} ) and x['engine_status'].get('ok')]
    if len(statuses)>1:out['measured_fps']=(statuses[-1][1]-statuses[0][1])/(statuses[-1][0]-statuses[0][0])
(r/'reports'/f'{tag}.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:v for k,v in out.items() if k not in ['samples','command']},indent=2))
