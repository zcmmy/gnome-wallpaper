#!/usr/bin/env python3
"""Download exact Debian source inputs into an explicit output directory, never install packages.
Requires enabled deb-src indices. Fail rather than silently substituting another version.
"""
import argparse,json,pathlib,subprocess,hashlib
p=argparse.ArgumentParser();p.add_argument('manifest',type=pathlib.Path);p.add_argument('destination',type=pathlib.Path);a=p.parse_args()
a.destination.mkdir(parents=True,exist_ok=True)
data=json.loads(a.manifest.read_text());packages=sorted({(r['source_package'],r['source_version']) for r in data['libraries']+data.get('source_inputs',[]) if 'source_package' in r})
for name,version in packages:
    subprocess.run(['apt-get','source','--download-only','--only-source',name+'='+version],cwd=a.destination,check=True)
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.destination.iterdir()) if p.is_file() and p.name!='sources.json'}
(a.destination/'sources.json').write_text(json.dumps({'packages':packages,'files':files},indent=2)+'\n')
