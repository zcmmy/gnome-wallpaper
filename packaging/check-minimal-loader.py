#!/usr/bin/env python3
"""Load the packaged ELF with only its private closure and enumerated host ABI libraries."""
import argparse,json,pathlib,re,subprocess,tempfile,zipfile,importlib.util
p=argparse.ArgumentParser();p.add_argument('archive',type=pathlib.Path);a=p.parse_args()
spec=importlib.util.spec_from_file_location('installer',pathlib.Path(__file__).with_name('install.py'));installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
with tempfile.TemporaryDirectory(prefix='wallpaper-minimal-') as tmp:
 stage=pathlib.Path(tmp);installer.extract(a.archive,stage);backend=stage/'backend/linux-x86_64';m=json.loads((backend/'manifest.json').read_text())
 cache=subprocess.check_output(['/sbin/ldconfig','-p'],text=True)
 libraries={name:path for name,path in re.findall(r'^\s*(\S+) \(libc6,x86-64[^)]*\) => (.+)$',cache,re.M)}
 command=['bwrap','--unshare-net','--tmpfs','/','--proc','/proc','--dev','/dev','--dir','/tmp','--ro-bind',str(backend),'/package','--ro-bind','/lib64/ld-linux-x86-64.so.2','/lib64/ld-linux-x86-64.so.2']
 for name in m['host']['libraries']:
  if name not in libraries:raise SystemExit('Missing declared host ABI: '+name)
  command+=['--ro-bind',str(pathlib.Path(libraries[name]).resolve()),'/host/lib/'+name]
 command+=['--setenv','LD_LIBRARY_PATH','/package/lib:/host/lib','--setenv','HOME','/tmp','--chdir','/tmp','/package/bin/linux-wallpaperengine','--version']
 result=subprocess.run(command,capture_output=True,text=True)
 if result.returncode:raise SystemExit(result.stderr+result.stdout)
 print('PASS: packaged ELF loads with only private libraries and',len(m['host']['libraries']),'declared host ABI libraries')
