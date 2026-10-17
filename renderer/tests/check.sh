#!/bin/bash
set -euo pipefail
source "$(dirname "$(readlink -f "$0")")/../scripts/env.sh"
source_dir="$WALLPAPER_ROOT/renderer/source/src"
renderer_output="${WALLPAPER_BUILD_DIR:-$WALLPAPER_ROOT/build/renderer}/output"
if [ -z "${WALLPAPER_BUILD_DIR:-}" ] && [ ! -f "$renderer_output/liblinux-wallpaperengine-lib.so" ]; then
    renderer_output="$WALLPAPER_ROOT/build/portghost/output"
fi
test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT
"${CXX:-g++}" -std=c++20 -I"$source_dir" "$WALLPAPER_ROOT/renderer/tests/check-spectrum.cpp" -o "$test_dir/spectrum"
"$test_dir/spectrum"
"${CXX:-g++}" -std=c++20 -I"$source_dir" -I"$source_dir/External/json/single_include" \
    "$WALLPAPER_ROOT/renderer/tests/check-pointer.cpp" "$source_dir/WallpaperEngine/Api/CommandDispatcher.cpp" -o "$test_dir/pointer"
"$test_dir/pointer"

"${CXX:-g++}" -std=c++20 -I"$source_dir" -I"$source_dir/External/json/single_include" \
    "$WALLPAPER_ROOT/renderer/tests/check-video-texture.cpp" -L"$renderer_output" \
    -llinux-wallpaperengine-lib -o "$test_dir/video-texture"
LD_LIBRARY_PATH="$renderer_output:${LD_LIBRARY_PATH:-}" "$test_dir/video-texture"

"${CXX:-g++}" -std=c++20 -O2 -Wall -Wextra -I"$source_dir" "$WALLPAPER_ROOT/renderer/tests/check-capture.cpp" -o "$test_dir/capture"
"$test_dir/capture"

"${CXX:-g++}" -std=c++20 -I"$source_dir" -I"$source_dir/External/json/single_include" \
    "$WALLPAPER_ROOT/renderer/tests/check-capture-command.cpp" "$source_dir/WallpaperEngine/Api/CommandDispatcher.cpp" -o "$test_dir/capture-command"
"$test_dir/capture-command"
