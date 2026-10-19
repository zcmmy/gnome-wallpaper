# Build-script copyright and licenses

The module headers retain their original authors and license declarations.
These files are not relicensed under the renderer's GPL.

| Module | Attribution in the source | License text |
| --- | --- | --- |
| FindMPV.cmake | Based on Michael Jansen's FindVLC; modified by Tobias Hieta | [COPYING-CMAKE-SCRIPTS](COPYING-CMAKE-SCRIPTS), BSD-3-Clause |
| FindPulseAudio.cmake | Matthias Kretz (2008), Marcus Hufgard (2009) | [COPYING-CMAKE-SCRIPTS](COPYING-CMAKE-SCRIPTS), BSD-3-Clause |
| FindFFMPEG.cmake | Andreas Schneider (2008), Lasse Kärkkäinen, Stepik777, Tuukka Pasanen (2018) | New BSD declaration; [COPYING-CMAKE-SCRIPTS](COPYING-CMAKE-SCRIPTS), BSD-3-Clause |
| FindDBus.cmake | Raphael Kubo da Costa (2012) | Complete BSD-2-Clause notice in its header |
| DownloadCEF.cmake | The Chromium Embedded Framework Authors (2016) | [LICENSE-CEF](LICENSE-CEF), BSD-3-Clause |

`COPYING-CMAKE-SCRIPTS` supplies the BSD terms declared by these headers, using
[KDE Extra CMake Modules' published text](https://github.com/KDE/extra-cmake-modules/blob/master/COPYING-CMAKE-SCRIPTS),
checked on 2026-10-19. Copyright holders remain those in each module header.
This is a downstream restoration of missing license terms, not a claim that we
recovered the exact historical license file from which every module was copied.

`LICENSE-CEF` is copied verbatim from the downloaded CEF distribution pinned in
[sources.lock.json](../../../third_party/sources.lock.json), version
`135.0.17+gcbc1c5b+chromium-135.0.7049.52_linux64_minimal`.
SHA-256: `058c3827ffb827ff3edda471ae7e1bb1d1aa5931985f0126043ccd33409e792f`.
It covers CEF's own code and this build helper, not all Chromium third-party code.
A full CEF runtime distribution needs its additional third-party notices.

The helper code came through the [portghost baseline](https://github.com/portghost-dev/linux-wallpaperengine/blob/50530e5167c0822e63f052f50ef8d8613663915a/CMakeModules).
Apart from correcting license-file references, its build behavior is unchanged.
