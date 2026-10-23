#!/usr/bin/python3
"""Private loader: never modify the Shell or preferences process environment."""
import json,os,pathlib,platform,subprocess,sys
root=pathlib.Path(__file__).resolve().parent.parent
manifest=json.loads((root/'manifest.json').read_text())
if platform.machine()!='x86_64' or manifest.get('protocol')!=1:raise SystemExit('Unsupported backend architecture/protocol')
exe=root/'bin/linux-wallpaperengine'
env=dict(os.environ,LD_LIBRARY_PATH=str(root/'lib'),vblank_mode=os.environ.get('vblank_mode','0'))
if sys.argv[1:]==['--capabilities']:
    print(json.dumps({k:manifest[k] for k in ['protocol','version','platform','capabilities']}));raise SystemExit(0)
if sys.argv[1:]==['--check']:
    p=subprocess.run(['ldd',str(exe)],env=env,capture_output=True,text=True)
    if p.returncode or 'not found' in p.stdout:raise SystemExit(p.stdout+p.stderr)
    subprocess.run([str(exe),'--version'],env=env,check=True);raise SystemExit(0)
# Renderer cache belongs to XDG_CACHE_HOME. The installation remains read-only.
cache=pathlib.Path(os.environ.get('XDG_CACHE_HOME',str(pathlib.Path.home()/'.cache')))/'gnome-wallpaper/renderer'
cache.mkdir(parents=True,exist_ok=True,mode=0o700);os.chdir(cache)
os.execve(exe,[str(exe),*sys.argv[1:]],env)
