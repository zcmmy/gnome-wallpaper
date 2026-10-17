#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
# Retain the optional portghost argument for existing callers.
if [ "${1:-}" = portghost ]; then shift; fi
if [ "$#" -gt 0 ] && [[ "$1" != --* ]]; then
    echo 'Usage: renderer/scripts/preview.sh [portghost] [--engine-options...]' >&2; exit 2
fi
exec "$root/renderer/scripts/run.sh" --window 100x100x960x540 --fps 30 --silent \
    --assets-dir "${WALLPAPER_ASSETS:-$root/assets}" "$@" "${WALLPAPER_SCENE:-$root/wallpaper}"
