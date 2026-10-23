#!/usr/bin/env python3
"""Create a relocatable scene runtime for the current Linux host; never install it."""
import argparse, hashlib, json, os, pathlib, re, shutil, subprocess, tempfile
from runtime_notices import collect_notices
p=argparse.ArgumentParser(); p.add_argument('destination',type=pathlib.Path);a=p.parse_args()
r=pathlib.Path(__file__).resolve().parents[2]
d=a.destination.absolute()
if d.exists():raise SystemExit('Destination already exists; choose a new directory.')
source=r/'build/renderer/output'
if not (source/'linux-wallpaperengine').exists():source=r/'build/portghost/output'
if not source.exists():raise SystemExit('Build the renderer first.')
local=r/'deps/sysroot/usr'
env=os.environ.copy();env['LD_LIBRARY_PATH']=f'{source}:{local}/lib/x86_64-linux-gnu:{local}/lib'
linked=subprocess.check_output(['ldd',str(source/'linux-wallpaperengine')],env=env,text=True)
if 'not found' in linked:raise SystemExit(linked)
libs={};system=[]
for name,path in re.findall(r'^\s*(\S+) => (\S+) \(',linked,re.M):
 q=pathlib.Path(path)
 if q.is_relative_to(r):libs[name]=q.resolve()
 else:system.append(name)
def write(path,text,executable=False):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
 if executable:path.chmod(0o755)
d.parent.mkdir(parents=True,exist_ok=True)
stage=pathlib.Path(tempfile.mkdtemp(prefix='.wallpaper-runtime-',dir=d.parent))
try:
 for name in ['bin','libexec','lib','gnome','licenses']: (stage/name).mkdir()
 # Include source/embedded-code notices as well as the actual private library notices.
 collect_notices(r, local, source, stage/'licenses', libs)
 shutil.copy2(source/'linux-wallpaperengine',stage/'libexec/linux-wallpaperengine')
 for name,path in libs.items():shutil.copy2(path,stage/'lib'/name)
 shutil.copytree(r/'assets',stage/'assets',symlinks=False)
 shutil.copytree(r/'wallpaper',stage/'wallpaper',symlinks=False)
 shutil.copytree(r/'wallpapers',stage/'wallpapers',symlinks=False)
 ext=stage/'gnome/wallpaperengine@waylandwe';(ext/'schemas').mkdir(parents=True)
 for name in [p.name for p in (r/'gnome/extension').glob('*.js')] + ['metadata.json','libraryWorker.py','captureWorker.py']:
  shutil.copy2(r/'gnome/extension'/name,ext/name)
 for f in (r/'gnome/extension/schemas').glob('*.gschema.xml'):shutil.copy2(f,ext/'schemas'/f.name)
 subprocess.run(['glib-compile-schemas','--strict',str(ext/'schemas')],check=True)
 shutil.copy2(r/'renderer/source/LICENSE',stage/'licenses/renderer-LICENSE')
 for name in ['LICENSE','NOTICE.md']:
  shutil.copy2(r/name,stage/name)
  shutil.copy2(r/name,ext/name)
 write(stage/'bin/renderer','''#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
export LD_LIBRARY_PATH="$root/lib"
export vblank_mode="${vblank_mode:-0}"
cd "$root"
exec "$root/libexec/linux-wallpaperengine" "$@"
''',True)
 shutil.copy2(r/'gnome/scripts/install-extension.py',stage/'libexec/install-extension.py')
 write(stage/'bin/install-gnome', '''#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
exec python3 "$root/libexec/install-extension.py" "$root/gnome/wallpaperengine@waylandwe" "${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/wallpaperengine@waylandwe"
''',True)
 write(stage/'bin/manager','''#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
exec gjs -m "$root/gnome/wallpaperengine@waylandwe/managerApp.js" "$@"
''',True)
 write(stage/'bin/capture-static','''#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
exec python3 "$root/gnome/wallpaperengine@waylandwe/captureWorker.py" --renderer "$root/bin/renderer" --assets "$root/assets" "$@"
''',True)
 write(stage/'bin/preview','''#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
exec "$root/bin/renderer" --window 100x100x960x540 --fps 30 --silent --no-fullscreen-pause \\
    --assets-dir "$root/assets" "$@" "$root/wallpaper"
''',True)
 write(stage/'bin/check-runtime','''#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
libs=$(LD_LIBRARY_PATH="$root/lib" ldd "$root/libexec/linux-wallpaperengine")
if [[ "$libs" == *"not found"* ]]; then printf '%s\\n' "$libs" >&2; exit 1; fi
printf '%s\\n' 'PASS: all runtime libraries resolved'
test -d "$root/assets/models"
test -d "$root/assets/shaders"
test -f "$root/wallpaper/scene.pkg"
test -f "$root/gnome/wallpaperengine@waylandwe/schemas/gschemas.compiled"
printf '%s\\n' 'PASS: scene, assets and GNOME extension present'
''',True)
 write(stage/'bin/configure-gnome','''#!/bin/bash
# Explicit configuration only. Does not install/enable the extension or autostart.
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
export GSETTINGS_SCHEMA_DIR="$root/gnome/wallpaperengine@waylandwe/schemas"
schema=org.gnome.shell.extensions.wallpaperengine
gsettings set "$schema" wallpaperengine-path "$root/bin/renderer"
gsettings set "$schema" assets-path "$root/assets"
gsettings set "$schema" library-root "$root/wallpapers"
gsettings reset "$schema" selected-id
gsettings set "$schema" enabled false
gsettings set "$schema" rotation-enabled false
gsettings set "$schema" rotation-interval 30
gsettings set "$schema" wallpaper-id "$root/wallpaper"
gsettings set "$schema" engine wallpaperengine
gsettings set "$schema" fps 15
printf '%s\\n' 'Paths configured. Extension activation remains manual.'
''',True)
 write(stage/'bin/restore-background','''#!/usr/bin/gjs -m
import Gio from 'gi://Gio';
import {restoreStaticWallpaper} from '../gnome/wallpaperengine@waylandwe/staticWallpaper.js';
if (!restoreStaticWallpaper()) throw new Error('No original background backup or settings not writable');
Gio.Settings.sync();
print('Original background restored.');
''',True)
 shutil.copy2(r/'docs/RUNTIME.md', stage/'README.md')
 files={str(f.relative_to(stage)):hashlib.sha256(f.read_bytes()).hexdigest() for f in stage.rglob('*') if f.is_file()}
 manifest={'format':1,'profile':'scene','os':pathlib.Path('/etc/os-release').read_text(),'arch':os.uname().machine,'project_version':(r/'VERSION').read_text().strip(),'project_commit':subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip(),'renderer_commit':json.loads((r/'third_party/sources.lock.json').read_text())['components'][0]['commit'],'renderer_has_local_patches':True,'gnome_revision':14,'mutable_directories':['wallpapers/'],'mutable_files':[name for name in files if name.startswith('wallpapers/') and name.endswith(('/static-background.png','/thumbnail.jpg'))],'bundled_libraries':sorted(libs),'system_libraries':sorted(system),'files_sha256':files}
 write(stage/'manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 # No symlinks: every program, library and asset really belongs to this directory.
 assert not any(f.is_symlink() for f in stage.rglob('*'))
 stage.rename(d)
 print(json.dumps({'destination':str(d),'bundled_libraries':len(libs),'size_bytes':sum(f.stat().st_size for f in d.rglob('*') if f.is_file())},ensure_ascii=False))
except BaseException:
 shutil.rmtree(stage,ignore_errors=True);raise
