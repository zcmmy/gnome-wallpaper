#!/bin/bash
set -euo pipefail
source "$(dirname "$(readlink -f "$0")")/env.sh"
cd "$WALLPAPER_ROOT"
renderer_bin="${WALLPAPER_RENDERER_BIN:-$WALLPAPER_ROOT/build/renderer/output/linux-wallpaperengine}"
if [ -z "${WALLPAPER_RENDERER_BIN:-}" ] && [ ! -x "$renderer_bin" ]; then
    renderer_bin="$WALLPAPER_ROOT/build/portghost/output/linux-wallpaperengine"
fi
if [ ! -x "$renderer_bin" ]; then
    echo 'Renderer not built. Run renderer/scripts/build.sh, or set WALLPAPER_RENDERER_BIN.' >&2; exit 2
fi
export vblank_mode="${vblank_mode:-0}"
renderer_runtime="${WALLPAPER_RUNTIME_DIR:-$WALLPAPER_ROOT/runtime}"
export XDG_CACHE_HOME="$renderer_runtime/cache"
export XDG_CONFIG_HOME="$renderer_runtime/config"
export XDG_STATE_HOME="$renderer_runtime/state"
exec "$renderer_bin" "$@"
