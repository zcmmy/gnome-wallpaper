"""Stage a fresh module URL for the explicit Looking Glass Forge update."""
from pathlib import Path
import shutil
import sys


def stage(source, destination):
    # Never reuse an imported module URL for a different implementation.
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__'))
    overview = destination / 'overviewWallpaper.js'
    # Shell GTypes are process-global even when ES modules have distinct URLs.
    overview.write_text(overview.read_text().replace('WallpaperAdapterOverviewClip',
        'WallpaperAdapterForgeOverviewClip13').replace('WallpaperAdapterOverviewSurface',
        'WallpaperAdapterForgeOverviewSurface13'))


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
