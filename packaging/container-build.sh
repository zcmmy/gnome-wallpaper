#!/bin/bash
# For a disposable Debian 13 build container only; never modifies the user's host.
set -euo pipefail
if [ ! -e /.dockerenv ] && [ ! -e /run/.containerenv ]; then
    echo 'Run this recipe only inside a disposable Debian 13 container.' >&2; exit 2
fi
cd "$(dirname "$0")/.."
mapfile -t packages < <(python3 -c 'import json; p=json.load(open("packaging/debian13-build.lock.json")); print("\n".join(k+"="+v for k,v in p["packages"].items()))')
apt-get update
apt-get install --yes --no-install-recommends "${packages[@]}"
# Fixed versions are intentional; unavailable inputs fail rather than selecting newer packages.
mkdir -p deps
ln -s / deps/sysroot
python3 -c 'import json; p=json.load(open("packaging/debian13-build.lock.json")); open("deps/packages.txt","w").write("\n".join(k+"="+v for k,v in p["packages"].items())+"\n")'
bash packaging/build-backend.sh
WALLPAPER_BUILD_DIR="$PWD/build/package-renderer" make check
python3 packaging/build-package.py --build-dir build/package-renderer --output dist/development
python3 packaging/fetch-sources.py dist/development/backend-manifest.json build/dependency-sources
WALLPAPER_DEPENDENCY_SOURCES="$PWD/build/dependency-sources" make release-package
