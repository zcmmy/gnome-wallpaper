#!/usr/bin/env python3
"""Build the public plugin release; never include local runtime or user resources."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[2]
version = (root / 'VERSION').read_text().strip()
if not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', version):
    raise SystemExit('Expected semantic project VERSION')
if len(sys.argv) > 2:
    raise SystemExit('Usage: package-release.py [NEW_OUTPUT_DIRECTORY]')
out = Path(sys.argv[1]).absolute() if len(sys.argv) == 2 else root / 'build/releases' / version
out.mkdir(parents=True, exist_ok=False)
archive = out / f'gnome-wallpaper-{version}.shell-extension.zip'
subprocess.run(['bash', str(root / 'gnome/scripts/build.sh'), str(archive)], check=True)
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:
        raise SystemExit('Invalid ZIP')
    names = set(z.namelist())
    required = {'LICENSE', 'NOTICE.md', 'VERSION', 'metadata.json', 'extension.js', 'prefs.js',
                'compositingGuard.js', 'captureWorker.py', 'libraryWorker.py', 'schemas/gschemas.compiled'}
    assert required <= names, required - names
    assert z.read('VERSION').decode().strip() == version
    metadata = json.loads(z.read('metadata.json'))
    assert metadata['uuid'] == 'wallpaperengine@waylandwe'
    assert metadata['url'] == 'https://github.com/zcmmy/gnome-wallpaper'
    for name in names:
        # Explicit extension-only allowlist; no hidden local state or media assets.
        assert (name in {'LICENSE', 'NOTICE.md', 'VERSION', 'metadata.json', 'schemas/gschemas.compiled'}
                or ('/' not in name and name.endswith(('.js', '.py')))
                or (name.startswith('schemas/') and name.endswith('.gschema.xml'))), name
    for name in names:
        if name.endswith('.js'):
            for ref in re.findall(r"from ['\"]\./([^'\"]+)['\"]", z.read(name).decode()):
                assert ref in names, (name, ref)
shutil.copyfile(root / 'gnome/scripts/install-extension.py', out / 'install-extension.py')
shutil.copyfile(root / 'docs/PLUGIN-INSTALL.md', out / f'INSTALL-{version}.md')
files = sorted(out.iterdir())
(out / 'SHA256SUMS').write_text(''.join(
    f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in files))
print(out)
