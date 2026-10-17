#!/bin/bash
set -euo pipefail
gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell/WallpaperAdapterTrial --method org.wallpaper.Adapter.Trial.Stop
