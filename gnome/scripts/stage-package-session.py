#!/usr/bin/env python3
"""Prepare explicit session-only modules; never touch the installed program tree."""
import argparse,hashlib,json,pathlib,shutil
p=argparse.ArgumentParser(description=__doc__);p.add_argument('installed',type=pathlib.Path);p.add_argument('state',type=pathlib.Path);a=p.parse_args()
installed=a.installed.resolve();manifest=(installed/'package-manifest.json').read_bytes();identity=hashlib.sha256(manifest).hexdigest()[:16]
if json.loads(manifest).get('backend_protocol')!=1:raise SystemExit('Unsupported package')
a.state.mkdir(parents=True,exist_ok=True,mode=0o700);stage=a.state/'session-code'/identity
if not stage.exists():
 stage.mkdir(parents=True,mode=0o700)
 for source in installed.glob('*.js'):shutil.copy2(source,stage/source.name)
 shutil.copy2(installed/'captureWorker.py',stage/'captureWorker.py')
 shutil.copytree(installed/'common',stage/'common')
 path=stage/'common/paths.js';text=path.read_text();text=text.replace('export const extensionRoot = Gio.File.new_for_uri(import.meta.url).get_parent().get_parent().get_path();','export const extensionRoot = '+json.dumps(str(installed))+';');path.write_text(text)
 path=stage/'overviewWallpaper.js';text=path.read_text().replace("GTypeName:'WallpaperAdapterOverviewClip'","GTypeName:'WallpaperPackageClip"+identity+"'").replace("GTypeName:'WallpaperAdapterOverviewSurface'","GTypeName:'WallpaperPackageSurface"+identity+"'");path.write_text(text)
record={'identity':identity,'installed':str(installed),'module':str(stage/'wallpaperExtension.js')}
(a.state/'session-package.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
