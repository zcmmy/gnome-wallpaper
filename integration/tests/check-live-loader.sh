#!/bin/bash
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/../.."
ROOT="$PWD"
export XDG_CONFIG_HOME="$ROOT/runtime/compat-test/config"
export XDG_DATA_HOME="$ROOT/runtime/compat-test/data"
export XDG_CACHE_HOME="$ROOT/runtime/compat-test/cache"
export XDG_STATE_HOME="$ROOT/runtime/compat-test/state"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME/gnome-shell/extensions" "$XDG_CACHE_HOME" "$XDG_STATE_HOME"
cp -r "$HOME/.local/share/gnome-shell/extensions/." "$XDG_DATA_HOME/gnome-shell/extensions/"
BOOT="$XDG_DATA_HOME/gnome-shell/extensions/wallpaper-trial-test@local"
mkdir -p "$BOOT"
cat > "$BOOT/metadata.json" <<'JSON'
{"uuid":"wallpaper-trial-test@local","name":"Isolated test bootstrap","description":"Local test only","shell-version":["48"]}
JSON
cat > "$BOOT/extension.js" <<'JS'
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import Gio from 'gi://Gio';
const Live = await import(Gio.File.new_for_path(GLib.getenv('ROOT') + '/gnome/scripts/live-desktop.js').get_uri());
export default class Test extends Extension {
 enable() {
  GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
   Live.start().then(s => console.warn('LIVE-TEST ' + s)).catch(e => console.error('LIVE-TEST ERROR ' + e.message + '\n' + e.stack));
   return GLib.SOURCE_REMOVE;
  });
  GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 22, () => {
   try {console.warn('LIVE-TEST SNAPSHOT ' + JSON.stringify(Live.snapshot()));} catch(e) {console.error('LIVE-TEST ERROR '+e.stack);}
   Live.stop().finally(() => global.context.terminate());
   return GLib.SOURCE_REMOVE;
  });
 }
 disable() {}
}
JS
export ROOT
export GSETTINGS_SCHEMA_DIR="$ROOT/gnome/extension/schemas"
exec dbus-run-session -- bash -c '
set -euo pipefail
dconf load /org/gnome/shell/ < "$ROOT/runtime/live-desktop/shell-before.dconf"
gsettings set org.gnome.shell.extensions.wallpaperengine engine wallpaperengine
gsettings set org.gnome.shell.extensions.wallpaperengine wallpaper-id "$ROOT/wallpaper"
gsettings set org.gnome.shell.extensions.wallpaperengine assets-path "$ROOT/assets"
gsettings set org.gnome.shell.extensions.wallpaperengine wallpaperengine-path "$ROOT/renderer/scripts/run.sh"
gsettings set org.gnome.shell.extensions.wallpaperengine fps 30
gsettings set org.gnome.shell enabled-extensions "[\"dash-to-dock@micxgx.gmail.com\",\"drive-menu@gnome-shell-extensions.gcampax.github.com\",\"rounded-windows@marcosgt.github.io\",\"blur-my-shell@aunetx\",\"wallpaper-trial-test@local\"]"
exec gnome-shell --headless --virtual-monitor=1280x720 --wayland --wayland-display wallpaper-compat-test --no-x11 --sm-disable
'
