#!/bin/bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/../.."
ROOT="$PWD"
export XDG_CONFIG_HOME="$ROOT/runtime/nested/config"
export XDG_DATA_HOME="$ROOT/runtime/nested/data"
export XDG_CACHE_HOME="$ROOT/runtime/nested/cache"
export XDG_STATE_HOME="$ROOT/runtime/nested/state"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME/gnome-shell/extensions" "$XDG_CACHE_HOME" "$XDG_STATE_HOME"
EXT="$XDG_DATA_HOME/gnome-shell/extensions/wallpaperengine@waylandwe"
mkdir -p "$EXT"
cp gnome/extension/*.js gnome/extension/metadata.json "$EXT/"
cp integration/tests/nested-test-driver.js "$EXT/testDriver.js"
sed -i '/argv.push(scene);/i\        argv.push("--screenshot", GLib.getenv("WALLPAPER_TEST_ROOT") + "/reports/gnome-render.png");' "$EXT/wallpaperExtension.js"
printf '\nimport {startTest} from "./testDriver.js";\n' >> "$EXT/wallpaperExtension.js"
sed -i '/this._settings = this.getSettings();/a\        GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {startTest(this); return GLib.SOURCE_REMOVE;});' "$EXT/wallpaperExtension.js"
cp -r gnome/extension/schemas "$EXT/"
glib-compile-schemas "$EXT/schemas"
export GSETTINGS_SCHEMA_DIR="$EXT/schemas"
export WALLPAPER_TEST_ROOT="$ROOT"
export LWE_POINTERPROBE=1
exec dbus-run-session -- bash -c '
set -euo pipefail
printf "%s" "$DBUS_SESSION_BUS_ADDRESS" > "$WALLPAPER_TEST_ROOT/runtime/nested/bus-address"
gsettings set org.gnome.shell.extensions.wallpaperengine enabled true
gsettings set org.gnome.shell.extensions.wallpaperengine engine wallpaperengine
gsettings set org.gnome.shell.extensions.wallpaperengine wallpaper-id "$WALLPAPER_TEST_ROOT/wallpaper"
gsettings set org.gnome.shell.extensions.wallpaperengine assets-path "$WALLPAPER_TEST_ROOT/assets"
gsettings set org.gnome.shell.extensions.wallpaperengine wallpaperengine-path "$WALLPAPER_TEST_ROOT/renderer/scripts/run.sh"
gsettings set org.gnome.shell.extensions.wallpaperengine fps 30
gsettings set org.gnome.shell enabled-extensions "[\"wallpaperengine@waylandwe\"]"
gsettings set org.gnome.shell disable-user-extensions false
gsettings set org.gnome.shell welcome-dialog-last-shown-version "48.0"
exec gnome-shell --headless --virtual-monitor=1280x720 --wayland --wayland-display wallpaper-adapter-test --no-x11 --sm-disable --debug-control
'
