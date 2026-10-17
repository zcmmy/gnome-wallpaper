#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <span>
#include <stdexcept>
#include <vector>

namespace WallpaperEngine::Render::Capture {
struct Tap { int index; double weight; };
using Axis = std::vector<std::vector<Tap>>;

// UVs describe pixel EDGES. Minification integrates the full source footprint;
// magnification interpolates at destination pixel CENTERS. Reversed UVs and
// out-of-range coordinates retain the screenshot path's clamp-to-edge behavior.
inline Axis weights(int source, int destination, double start, double end) {
    if (source <= 0 || destination <= 0 || !std::isfinite(start) || !std::isfinite(end))
        throw std::invalid_argument("Invalid capture dimensions or UVs");
    const double first = start * source, step = (end - start) * source / destination;
    if (!std::isfinite(first) || !std::isfinite(step)) throw std::invalid_argument("Invalid capture UV range");
    Axis axis(destination);
    for (int i = 0; i < destination; ++i) {
        auto& taps = axis[i];
        const auto add = [&](int index, double weight) {
            if (weight <= 0) return;
            if (!taps.empty() && taps.back().index == index) taps.back().weight += weight;
            else taps.push_back({index, weight});
        };
        if (std::abs(step) > 1.0 + 1e-9) {
            const double edge1 = first + i * step, edge2 = edge1 + step;
            const double left = std::min(edge1, edge2), right = std::max(edge1, edge2);
            const double span = right - left;
            // Integrate the clamped outside area without iterating out of bounds.
            add(0, std::max(0.0, std::min(right, 0.0) - left) / span);
            const double a = std::max(left, 0.0), b = std::min(right, double(source));
            if (a < b) {
                for (int x = int(std::floor(a)); x < int(std::ceil(b)); ++x)
                    add(x, (std::min(b, double(x + 1)) - std::max(a, double(x))) / span);
            }
            add(source - 1, std::max(0.0, right - std::max(left, double(source))) / span);
        } else {
            const double center = std::clamp(first + (i + 0.5) * step - 0.5, 0.0, double(source - 1));
            const int x = int(std::floor(center));
            add(x, 1.0 - (center - x));
            add(std::min(x + 1, source - 1), center - x);
        }
        double sum = 0;
        for (const auto& tap : taps) sum += tap.weight;
        if (!(sum > 0)) throw std::invalid_argument("Empty capture sampling footprint");
        for (auto& tap : taps) tap.weight /= sum;
    }
    return axis;
}
inline size_t rgbSize(int width, int height) {
    if (width <= 0 || height <= 0 || size_t(width) > std::numeric_limits<size_t>::max() / 3 / size_t(height))
        throw std::invalid_argument("Invalid capture size");
    return size_t(width) * size_t(height) * 3;
}
inline std::vector<uint8_t> resampleRgb(std::span<const uint8_t> source, int sw, int sh,
                                      int dw, int dh, double u0=0, double u1=1, double v0=0, double v1=1) {
    if (source.size() < rgbSize(sw, sh)) throw std::invalid_argument("Truncated capture buffer");
    const auto horizontal = weights(sw, dw, u0, u1), vertical = weights(sh, dh, v0, v1);
    // Float intermediate avoids quantizing between the two separable passes.
    std::vector<float> intermediate(rgbSize(dw, sh));
    std::vector<uint8_t> result(rgbSize(dw, dh));
    for (int y=0; y<sh; ++y) for (int x=0; x<dw; ++x) for (int c=0; c<3; ++c) {
        double value=0;
        for (const auto& tap : horizontal[x]) value += source[(size_t(y)*sw + tap.index)*3+c] * tap.weight;
        intermediate[(size_t(y)*dw+x)*3+c] = float(value);
    }
    for (int y=0; y<dh; ++y) for (int x=0; x<dw; ++x) for (int c=0; c<3; ++c) {
        double value=0;
        for (const auto& tap : vertical[y]) value += intermediate[(size_t(tap.index)*dw+x)*3+c] * tap.weight;
        result[(size_t(y)*dw+x)*3+c] = uint8_t(std::clamp(std::lround(value), 0L, 255L));
    }
    return result;
}
} // namespace WallpaperEngine::Render::Capture
