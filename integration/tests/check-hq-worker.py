import json,os,pathlib,signal,subprocess,time
r=pathlib.Path(__file__).resolve().parents[2];out=r/'reports/hq-capture'
args=['python3',str(r/'gnome/extension/captureWorker.py'),'--renderer',str(r/'renderer/scripts/run.sh'),'--assets',str(r/'assets'),'--scene',str(r/'wallpapers'/os.environ['WALLPAPER_TEST_REFERENCE']),'--output',str(out/'cancelled.png')]
def related():
 result=set()
 for path in pathlib.Path('/proc').glob('[0-9]*/cmdline'):
  try:
   data=path.read_bytes()
   if b'--wayland-display\0wallpaper-capture\0' in data or b'/tmp/wallpaper-hq-' in data:result.add(int(path.parent.name))
  except (OSError,ValueError):pass
 return result
before=related();p=subprocess.Popen(args,stdout=subprocess.PIPE,text=True)
time.sleep(3);children=related()-before
p.send_signal(signal.SIGTERM);text=p.communicate(timeout=12)[0]
time.sleep(.5)
assert p.returncode!=0 and not (out/'cancelled.png').exists(),text
assert not (related()-before),related()-before
print('PASS: cancelled capture reaps private compositor/renderer; no output exposed',children)
(out/'cancellation.json').write_text(json.dumps({'passed':True,'observed_children':sorted(children),'result':text,'remaining':[]},indent=2))
