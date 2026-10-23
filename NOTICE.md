# Copyright, licensing and upstream attribution

Copyright © 2026 GNOME Wallpaper contributors, for original integration work.
Existing code remains copyright its respective authors; original notices are retained.

GNOME Wallpaper's original code and modifications are distributed under the
**GNU General Public License, version 3 only (SPDX: GPL-3.0-only)**, except files
explicitly carrying another license. You may redistribute and modify this work
under those terms. It is provided without warranty, including implied warranties
of merchantability or fitness for a particular purpose. See [LICENSE](LICENSE)
for the complete terms.

## Renderer: portghost and Almamu

The renderer is derived from [portghost-dev/linux-wallpaperengine](https://github.com/portghost-dev/linux-wallpaperengine),
which extends [Almamu/linux-wallpaperengine](https://github.com/Almamu/linux-wallpaperengine).
The imported portghost baseline is
[`50530e5167c0822e63f052f50ef8d8613663915a`](https://github.com/portghost-dev/linux-wallpaperengine/tree/50530e5167c0822e63f052f50ef8d8613663915a).
Its README declares GPLv3, its Arch packaging declares GPL-3.0-only, and its
original license text is retained at `renderer/source/LICENSE`.

The resource parser, scene renderer, animation/scripting, particles and effects
are upstream work. This integration adds GNOME-specific input/embedding support,
spectrum and video compatibility fixes, and high-quality still capture.
Original upstream acknowledgments, including credits to ian-vinson, Haberno and
Intel's ISPC Texture Compressor contributors, remain in the renderer README.
GNOME Wallpaper is an independent downstream project, not an official release of
portghost, Almamu or Wallpaper Engine.

## GNOME extension

The original extension comes from
[diaslucass/wallpaperEngineWayland](https://github.com/diaslucass/wallpaperEngineWayland),
baseline [`e2ae60dc89a18235f315aee9dcca6a3b6fe89fa4`](https://github.com/diaslucass/wallpaperEngineWayland/tree/e2ae60dc89a18235f315aee9dcca6a3b6fe89fa4).
Its README explicitly declares **GPL-2.0-or-later**; absence of a separate LICENSE
file does not remove that declaration. The original declaration is preserved.
This modified distribution uses the GPLv3 option; it does not revoke the original
code's GPL-2.0-or-later grant.

## Separately licensed and user-provided content

The unused upstream `lwe-ui` control panel, its tests, the mixed installer and
demonstration images have been removed from this source distribution. The C++
renderer and its upstream attribution remain. External components retain their
respective license files and notices; see `third_party/licenses.json` and
`third_party/COMPONENT-NOTICES.md` in the source repository.
Text fallback uses the system Fontconfig library (MIT-style license); it is not
vendored here. Fontconfig source and license: https://gitlab.freedesktop.org/fontconfig/fontconfig .
FreeType and installed font files retain their own licensing; system font discovery
does not grant permission to redistribute fonts.

System libraries and CEF retain their own licenses. This notice does not relicense
them or their existing notices.

Wallpaper Engine assets, Workshop wallpapers, videos, audio, fonts and user still
images are not covered by the project's GPL grant. They are not included in the
source repository. Users must obtain and use such content under its own terms.

Source and modification history: https://github.com/zcmmy/gnome-wallpaper
When distributing binaries, provide the corresponding source and required notices
under the applicable licenses; this notice does not replace those obligations.
