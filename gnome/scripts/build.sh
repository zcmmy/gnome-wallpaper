#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
exec "$root/gnome/extension/scripts/package.sh" "${1:-$root/build/gnome/wallpaperengine@waylandwe.zip}"
