#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
source "$root/renderer/scripts/env.sh"
build="${WALLPAPER_BUILD_DIR:-$root/build/package-renderer}"
cmake -S "$root/renderer/source" -B "$build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
  "-DCMAKE_C_FLAGS=-ffile-prefix-map=$root=. -ffile-prefix-map=$(readlink -f "$root/deps")=./deps" \
  "-DCMAKE_CXX_FLAGS=-ffile-prefix-map=$root=. -ffile-prefix-map=$(readlink -f "$root/deps")=./deps"
cmake --build "$build" --target linux-wallpaperengine --parallel "${BUILD_JOBS:-4}"
