#pragma once
#include <algorithm>
#include <cstddef>

namespace WallpaperEngine::Audio {
// Keep narrow peaks when combining neighboring bands. Rebuild every frame so
// silence cannot retain peaks from the previous frame.
template <std::size_t N, std::size_t M>
void reduceSpectrumPeaks(const float (&input)[N], float (&output)[M]) {
    static_assert(N % M == 0);
    for (std::size_t i = 0; i < M; ++i) {
        output[i] = 0.0f;
        for (std::size_t j = 0; j < N / M; ++j)
            output[i] = std::max(output[i], input[i * (N / M) + j]);
    }
}
}
