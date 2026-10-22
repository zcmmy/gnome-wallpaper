#!/bin/bash
# Renderer toolchain only; safe to source from any working directory.
WALLPAPER_ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../.." && pwd)"
WALLPAPER_DEPS="$WALLPAPER_ROOT/deps/sysroot/usr"
if [ -d "$WALLPAPER_DEPS" ] && [ "$(readlink -f "$WALLPAPER_DEPS")" != /usr ]; then
    export PATH="$WALLPAPER_DEPS/bin:$PATH"
    export PKG_CONFIG_PATH="$WALLPAPER_DEPS/lib/x86_64-linux-gnu/pkgconfig:$WALLPAPER_DEPS/lib/pkgconfig:$WALLPAPER_DEPS/share/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
    export CMAKE_PREFIX_PATH="$WALLPAPER_DEPS${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
    export CPLUS_INCLUDE_PATH="$WALLPAPER_DEPS/include:$WALLPAPER_DEPS/include/x86_64-linux-gnu${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}"
    export C_INCLUDE_PATH="$WALLPAPER_DEPS/include:$WALLPAPER_DEPS/include/x86_64-linux-gnu${C_INCLUDE_PATH:+:$C_INCLUDE_PATH}"
    export LIBRARY_PATH="$WALLPAPER_DEPS/lib/x86_64-linux-gnu:$WALLPAPER_DEPS/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
    export LD_LIBRARY_PATH="$WALLPAPER_DEPS/lib/x86_64-linux-gnu:$WALLPAPER_DEPS/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
