#pragma once
#include <glm/vec2.hpp>
#include <glm/common.hpp>
#include <optional>
namespace WallpaperEngine::Input {
inline std::optional<glm::dvec2> logicalPointer(double x, double y, int width, int height) {
    if (width <= 0 || height <= 0) return std::nullopt;
    return glm::clamp(glm::dvec2{x / width, y / height}, glm::dvec2{0}, glm::dvec2{1});
}
inline glm::dvec2 framebufferPointer(glm::dvec2 normalized, glm::ivec2 framebuffer) {
    return {normalized.x * framebuffer.x, (1.0 - normalized.y) * framebuffer.y};
}
}
