#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/schemas" "$stage/scene"
cp "$root/gnome/extension/schemas/"*.gschema.xml "$stage/schemas/"
glib-compile-schemas --strict "$stage/schemas"
export GSETTINGS_SCHEMA_DIR="$stage/schemas"
export GIO_USE_VFS=local
python3 - "$stage/scene/static-background.png" <<'FIXTURE'
import struct, sys, zlib
from pathlib import Path
def chunk(tag, data):
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data))
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 2, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress((b'\x00' + b'\x22\x44\x66' * 2) * 2)) + chunk(b'IEND', b'')
Path(sys.argv[1]).write_bytes(png)
FIXTURE
XDG_STATE_HOME="$stage/state" GSETTINGS_BACKEND=memory gjs -m "$root/gnome/tests/check-static-wallpaper.js" "$stage/scene"
GSETTINGS_SCHEMA_DIR="$stage/schemas" XDG_STATE_HOME="$stage/state-manager" TEST_LIBRARY="$stage/library" GSETTINGS_BACKEND=memory dbus-run-session -- gjs -m "$root/gnome/tests/check-manager.js"
XDG_STATE_HOME="$stage/state-runtime-capture" TEST_LIBRARY="$stage/runtime-capture" GSETTINGS_BACKEND=memory dbus-run-session -- gjs -m "$root/gnome/tests/check-runtime-capture.js"
gjs "$root/gnome/tests/check-extension-restart.js" "$root/gnome/extension/wallpaperExtension.js"
gjs "$root/gnome/tests/check-compositing-guard.js" "$root/gnome/extension/compositingGuard.js"
gjs "$root/gnome/tests/check-forge-filter.js" "$root/gnome/extension/wallpaperExtension.js"
"$root/gnome/extension/scripts/package.sh" "$stage/extension.zip"
python3 - "$stage/extension.zip" <<'VERIFY'
import json,re,sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
 names=set(z.namelist())
 assert {'LICENSE','NOTICE.md','metadata.json','extension.js','prefs.js','libraryWorker.py','captureWorker.py','libraryOps.js','pointerBridge.js','overviewWallpaper.js','staticWallpaper.js','schemas/gschemas.compiled'} <= names
 assert json.loads(z.read('metadata.json'))['uuid']=='wallpaperengine@waylandwe'
 assert not any(n.endswith(('.cpp','.h','.so')) or '.git/' in n or 'renderer/' in n for n in names)
 for n in names:
  if n.endswith('.js'):
   for ref in re.findall(r"from ['\"]\./([^'\"]+)['\"]",z.read(n).decode()):
    assert ref in names,(n,ref)
print('PASS: extension archive includes local modules/schema and excludes the renderer')
VERIFY

python3 "$root/gnome/tests/check-schema-update.py"

mkdir -p "$root/runtime"
ops_stage="$(mktemp -d "$root/runtime/library-check-XXXXXX")"
trap 'rm -rf "$stage" "$ops_stage"' EXIT
TMPDIR="$ops_stage" GIO_USE_VFS=local GSETTINGS_SCHEMA_DIR="$stage/schemas" XDG_DATA_HOME="$ops_stage/data" XDG_STATE_HOME="$ops_stage/state" GSETTINGS_BACKEND=memory gjs -m "$root/gnome/tests/check-library-ops.js"
