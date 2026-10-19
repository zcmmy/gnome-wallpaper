# portghost renderer in GNOME Wallpaper

This is a modified, trimmed source snapshot of
[portghost-dev/linux-wallpaperengine](https://github.com/portghost-dev/linux-wallpaperengine),
which extends [Almamu/linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine).
The imported baseline is `50530e5167c0822e63f052f50ef8d8613663915a`.
The baseline identifies provenance; the enclosing GNOME Wallpaper Git revision identifies
our actual modified sources.

## Included scope

The C++ renderer, scene/script/animation/effect pipelines, input and command API,
build dependencies, renderer tests and synthetic calibration tools are retained.
The unused `lwe-ui` Qt/QML control panel, its tests and backup fixtures, the mixed
`install.sh` installer, and upstream `docs/images/` demonstrations have been removed.
One renderer help-output fixture was moved into `src/WallpaperEngine/Testing/Fixtures/`.
This does not remove any renderer feature or change the GNOME integration architecture.

GNOME Wallpaper uses its own [GNOME manager](../../gnome/extension).
Build with the top-level `make renderer`; follow [installation instructions](../../docs/INSTALL.md).
Some inherited `lwe` shorthand commands still target an external `lwe-ui` installation;
that optional upstream interface is not installed or used by this project.

[The original README](https://github.com/portghost-dev/linux-wallpaperengine/blob/50530e5167c0822e63f052f50ef8d8613663915a/README.md),
[Architecture](ARCHITECTURE.md) and [Fork map](docs/FORK-MAP.md) document the upstream
system. The latter two are historical references, not this distribution's installation
instructions. For the current integration see [architecture](../../docs/ARCHITECTURE.md).
Removal details and source/licensing records: [third_party](../../third_party/README.md).

## Credits

- [Almamu](https://github.com/Almamu) and the linux-wallpaperengine contributors.
  This fork stands entirely on their engine, and it is meant as a thank-you to
  that work, not a replacement for it.
- Fixes and ideas were adopted from the parallel forks by
  [ian-vinson](https://github.com/ian-vinson) and
  [Haberno](https://github.com/Haberno), including CEF bootstrap fixes, live
  property reload, audio device handling, config parsing, package lookup behavior,
  and parts of the shadow and tube-light work that extended this fork's existing
  lighting system. Their work is credited here rather than inline in the source.
- Texture compression uses Intel's
  [ISPC Texture Compressor](https://github.com/GameTechDev/ISPCTextureCompressor),
  vendored under `src/External/ISPCTextureCompressor/` and used under the MIT
  license included there.
- Wallpaper Engine itself is the work of
  [Kristjan Skutta](https://store.steampowered.com/app/431960/Wallpaper_Engine/).
  Wallpaper Engine assets and user wallpapers are separately licensed and are
  not distributed by GNOME Wallpaper.

## License

GPLv3, inherited from upstream; this distribution uses **GPL-3.0-only**.
See [LICENSE](LICENSE), [project NOTICE](../../NOTICE.md), and
[third-party license index](../../third_party/licenses.json) for separately licensed components.
The removed upstream UI declared MIT; no UI implementation is distributed here.
