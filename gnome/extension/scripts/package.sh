#!/bin/bash
# Build only the extension archive; no C++ build, package install or activation.
set -euo pipefail
extension_root="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
if [ "$#" -ne 1 ]; then echo 'Usage: scripts/package.sh OUTPUT.zip' >&2; exit 2; fi
output_zip="$1"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/schemas"
cp "$extension_root/../../LICENSE" "$extension_root/../../NOTICE.md" "$extension_root/../../VERSION" "$stage/"
cp "$extension_root"/captureWorker.py "$extension_root"/libraryWorker.py "$stage/"
cp "$extension_root"/*.js "$extension_root/metadata.json" "$stage/"
cp "$extension_root"/schemas/*.gschema.xml "$stage/schemas/"
glib-compile-schemas --strict "$stage/schemas"
python3 - "$stage" "$output_zip" <<'ARCHIVE'
from pathlib import Path
import sys,zipfile
stage=Path(sys.argv[1]);out=Path(sys.argv[2]).absolute()
if out.suffix != '.zip':raise SystemExit('Output must be a .zip file')
out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(stage.rglob('*')):
  if p.is_file():
   info=zipfile.ZipInfo(p.relative_to(stage).as_posix(),date_time=(1980,1,1,0,0,0))
   info.create_system=3
   info.external_attr=0o100644 << 16
   info.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(info,p.read_bytes(),compresslevel=9)
print(out)
ARCHIVE
