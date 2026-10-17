#include "WallpaperEngine/Audio/SpectrumBands.h"
#include <cassert>
#include <iostream>
int main() {
    float bands[64] = {}, b32[32] = {}, b16[16] = {};
    for (int peak = 0; peak < 64; ++peak) {
        std::fill_n(bands, 64, 0.0f);
        bands[peak] = .75f;
        WallpaperEngine::Audio::reduceSpectrumPeaks(bands, b32);
        WallpaperEngine::Audio::reduceSpectrumPeaks(bands, b16);
        for (int i = 0; i < 32; ++i) assert(b32[i] == (i == peak / 2 ? .75f : 0.0f));
        for (int i = 0; i < 16; ++i) assert(b16[i] == (i == peak / 4 ? .75f : 0.0f));
    }
    std::fill_n(bands, 64, 0.0f);
    WallpaperEngine::Audio::reduceSpectrumPeaks(bands, b32);
    WallpaperEngine::Audio::reduceSpectrumPeaks(bands, b16);
    for (auto v : b32) assert(v == 0);
    for (auto v : b16) assert(v == 0);
    std::cout << "PASS: all 64 peak positions survive 32/16 reduction; silence clears history\n";
}
