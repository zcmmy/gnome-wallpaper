#pragma once
#include <cstdint>
#include <string_view>

namespace WallpaperEngine::Render {
// Decode Unicode scalar values, never pass overlong sequences or UTF-16
// surrogates to a font. Consume one byte on error so following text survives.
inline uint32_t nextUtf8Codepoint(std::string_view text, size_t& offset) {
    if (offset >= text.size()) return 0xFFFD;
    const auto lead = static_cast<uint8_t>(text[offset]);
    if (lead < 0x80) { ++offset; return lead; }
    const unsigned count = lead >= 0xC2 && lead <= 0xDF ? 2 :
                           lead >= 0xE0 && lead <= 0xEF ? 3 :
                           lead >= 0xF0 && lead <= 0xF4 ? 4 : 0;
    if (!count || text.size() - offset < count) { ++offset; return 0xFFFD; }
    uint32_t code = lead & (0x7F >> count);
    for (unsigned i = 1; i < count; ++i) {
        const auto byte = static_cast<uint8_t>(text[offset + i]);
        if ((byte & 0xC0) != 0x80) { ++offset; return 0xFFFD; }
        code = (code << 6) | (byte & 0x3F);
    }
    if (code < (count == 2 ? 0x80u : count == 3 ? 0x800u : 0x10000u) ||
        code > 0x10FFFF || (code >= 0xD800 && code <= 0xDFFF)) {
        ++offset; return 0xFFFD;
    }
    offset += count;
    return code;
}
}
