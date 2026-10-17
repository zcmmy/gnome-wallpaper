#!/usr/bin/env python3
"""Sample an existing desktop renderer; do not start/stop it or change settings."""
from gi.repository import Gio,GLib
from pathlib import Path
import argparse,json,socket,time,os,statistics
P=argparse.ArgumentParser();P.add_argument('tag');P.add_argument('--seconds',type=int,default=30);a=P.parse_args()
assert a.tag.replace('-','').replace('_','').isalnum()
r=Path(__file__).resolve().parents[2];b=Gio.bus_get_sync(Gio.BusType.SESSION,None)
def desktop():
 return json.loads(b.call_sync('org.gnome.Shell','/org/gnome/Shell/WallpaperAdapterTrial','org.wallpaper.Adapter.Trial','Snapshot',None,GLib.VariantType('(s)'),Gio.DBusCallFlags.NONE,5000,None).unpack()[0])
j=desktop();pid=int(j['renderer']['pid']);path=j['renderer']['socket']
shell=b.call_sync('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetConnectionUnixProcessID',GLib.Variant('(s)',('org.gnome.Shell',)),GLib.VariantType('(u)'),Gio.DBusCallFlags.NONE,5000,None).unpack()[0]
def api(cmd='status',args=None):
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(2);s.connect(path);s.sendall((json.dumps({'id':1,'cmd':cmd,'args':args or {}})+'\n').encode());data=b''
  while b'\n' not in data:
   chunk=s.recv(65536)
   if not chunk:raise RuntimeError('socket closed')
   data+=chunk
  return json.loads(data)['result']
def memory_bytes(value):
 n,*unit=value.split();return float(n)*({'KiB':1024,'MiB':1024**2,'GiB':1024**3}.get(unit[0],1) if unit else 1)
def sample_process(pid):
 p=Path('/proc')/str(pid);stat=(p/'stat').read_text().split(') ',1)[1].split()
 info={'cpu_seconds':(int(stat[11])+int(stat[12]))/os.sysconf('SC_CLK_TCK')}
 for line in (p/'smaps_rollup').read_text().splitlines():
  if line.startswith(('Rss:','Pss:','Private_Dirty:')):k,v,*_=line.split();info[k[:-1]+'_mib']=int(v)/1024
 clients={}
 for f in (p/'fdinfo').iterdir():
  try:
   vals={k:v.strip() for k,v in (line.split(':',1) for line in f.read_text().splitlines() if ':' in line)}
   if 'drm-client-id' in vals:clients[vals['drm-client-id']]={k:v for k,v in vals.items() if k.startswith('drm-')}
  except OSError:pass
 info['drm_clients']=clients
 info['gpu_resident_mib']=sum(memory_bytes(v) for c in clients.values() for k,v in c.items() if k.startswith('drm-resident-'))/1024**2
 info['gpu_render_ns']=sum(int(c.get('drm-engine-render','0').split()[0]) for c in clients.values())
 return info
start=time.monotonic();out={'tag':a.tag,'renderer_pid':pid,'shell_pid':shell,'logical_cpus':os.cpu_count(),'status_before':api(),'samples':[]}
while True:
 now=time.monotonic();status=api()
 out['samples'].append({'t':now,'renderer':sample_process(pid),'shell':sample_process(shell),'gpu_freq_mhz':int(Path('/sys/class/drm/card0/gt/gt0/rps_cur_freq_mhz').read_text()),'frames':status['frames'],'pointer':status['pointer']})
 if now-start>=a.seconds:break
 time.sleep(1)
ss=out['samples'];dt=ss[-1]['t']-ss[0]['t'];summary={}
for proc in ['renderer','shell']:
 summary[proc]={'cpu_percent_one_core':100*(ss[-1][proc]['cpu_seconds']-ss[0][proc]['cpu_seconds'])/dt,'gpu_render_busy_percent':100*(ss[-1][proc]['gpu_render_ns']-ss[0][proc]['gpu_render_ns'])/(dt*1e9)}
 for key in ['Rss_mib','Pss_mib','gpu_resident_mib']:summary[proc][key]=statistics.median(s[proc][key] for s in ss)
 summary[proc]['cpu_percent_machine']=summary[proc]['cpu_percent_one_core']/os.cpu_count()
summary['fps']=(ss[-1]['frames']-ss[0]['frames'])/dt
summary['duration_s']=dt
summary['gpu_freq_mhz_median']=statistics.median(x['gpu_freq_mhz'] for x in ss)
summary['chrome_unchanged']=desktop()['chromeUnchanged']
out['summary']=summary;out['status_after']=api();(r/'reports'/('perf-'+a.tag+'.json')).write_text(json.dumps(out,indent=2));print(json.dumps(summary,indent=2))
