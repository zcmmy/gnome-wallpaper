#!/bin/bash
set -euo pipefail
source "$(dirname "$(readlink -f "$0")")/env.sh"
if [ "$#" -gt 1 ] || [ "${1:-portghost}" != portghost ]; then
    echo 'Usage: renderer/scripts/build.sh [portghost]' >&2; exit 2
fi
source_dir="$WALLPAPER_ROOT/renderer/source"
build_dir="$WALLPAPER_ROOT/build/renderer"
# Keep the existing CMake cache and the source path it records usable.
if [ ! -e "$build_dir/CMakeCache.txt" ] && [ -f "$WALLPAPER_ROOT/build/portghost/CMakeCache.txt" ]; then
    build_dir="$WALLPAPER_ROOT/build/portghost"
fi
build_dir="${WALLPAPER_BUILD_DIR:-$build_dir}"
if [ -f "$build_dir/CMakeCache.txt" ]; then
    cached_source=$(sed -n 's/^CMAKE_HOME_DIRECTORY:INTERNAL=//p' "$build_dir/CMakeCache.txt")
    if [ "$(readlink -f "$cached_source")" != "$(readlink -f "$source_dir")" ]; then
        echo "Refusing unrelated CMake cache: $build_dir" >&2; exit 2
    fi
    source_dir="$cached_source"
fi
cmake -S "$source_dir" -B "$build_dir" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
cmake --build "$build_dir" --parallel "${BUILD_JOBS:-4}"
