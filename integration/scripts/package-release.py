#!/usr/bin/env python3
"""Release assembly requires the full program package and corresponding dependency sources."""
import json,os,pathlib,subprocess,sys,hashlib,tarfile
root=pathlib.Path(__file__).resolve().parents[2]
source_dir=pathlib.Path(os.environ.get('WALLPAPER_DEPENDENCY_SOURCES','/nonexistent'))
source_index=source_dir/'sources.json'
if not source_index.is_file():raise SystemExit('Collect exact dependency sources with packaging/fetch-sources.py first; set WALLPAPER_DEPENDENCY_SOURCES. No incomplete Release will be built.')
version=(root/'VERSION').read_text().strip();out=pathlib.Path(sys.argv[1]).absolute() if len(sys.argv)>1 else root/'dist'/version
build=pathlib.Path(os.environ.get('WALLPAPER_BUILD_DIR',root/'build/package-renderer'))
subprocess.run([sys.executable,str(root/'packaging/build-package.py'),'--build-dir',str(build),'--output',str(out)],check=True)
manifest=json.loads((out/'backend-manifest.json').read_text());index=json.loads(source_index.read_text())
required={(r['source_package'],r['source_version']) for r in manifest['libraries']+manifest.get('source_inputs',[]) if 'source_package' in r}
if not required<={tuple(p) for p in index['packages']}:raise SystemExit('Dependency sources do not match the binary manifest')
for name,digest in index['files'].items():
 if pathlib.Path(name).name!=name or hashlib.sha256((source_dir/name).read_bytes()).hexdigest()!=digest:raise SystemExit('Dependency source hash mismatch')
with tarfile.open(out/'dependency-corresponding-sources.tar.gz','w:gz') as tar:
 for name in sorted(index['files']):tar.add(source_dir/name,arcname=name)
 tar.add(source_index,arcname='sources.json')
(out/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
print(out)
