#pragma once
#include <fontconfig/fontconfig.h>
#include <ft2build.h>
#include FT_FREETYPE_H
#include <algorithm>
#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>

namespace WallpaperEngine::Render {
// Own only fallback faces. The caller keeps the primary face and FT_Library
// alive. Lookups are cached across song changes; no filesystem work per frame.
class FontFallback {
    using Pattern = std::unique_ptr<FcPattern, decltype(&FcPatternDestroy)>;
    using Charset = std::unique_ptr<FcCharSet, decltype(&FcCharSetDestroy)>;
    using FontSet = std::unique_ptr<FcFontSet, decltype(&FcFontSetDestroy)>;
    FT_Library library;
    FT_Face primary;
    unsigned pixelSize = 1;
    std::unordered_map<std::string, FT_Face> faces;
    std::unordered_map<uint32_t, FT_Face> choices;

    static FT_Face open(FT_Library library, FcPattern* pattern) {
        FcChar8* path = nullptr;
        int index = 0;
        if (FcPatternGetString(pattern, FC_FILE, 0, &path) != FcResultMatch) return nullptr;
        FcPatternGetInteger(pattern, FC_INDEX, 0, &index); // TTC/OTC subface, not always zero.
        FT_Face face = nullptr;
        if (FT_New_Face(library, reinterpret_cast<const char*>(path), index, &face)) return nullptr;
        if (FT_Select_Charmap(face, FT_ENCODING_UNICODE)) { FT_Done_Face(face); return nullptr; }
        return face;
    }
public:
    FontFallback(FT_Library lib, FT_Face face) : library(lib), primary(face) {}
    FontFallback(const FontFallback&) = delete;
    FontFallback& operator=(const FontFallback&) = delete;
    ~FontFallback() { for (const auto& [key, face] : faces) FT_Done_Face(face); }

    static FT_Face systemFont(FT_Library library) {
        Pattern pattern(FcPatternCreate(), FcPatternDestroy);
        if (!pattern) return nullptr;
        FcPatternAddString(pattern.get(), FC_FAMILY, reinterpret_cast<const FcChar8*>("DejaVu Sans"));
        FcConfigSubstitute(nullptr, pattern.get(), FcMatchPattern);
        FcDefaultSubstitute(pattern.get());
        FcResult result;
        Pattern match(FcFontMatch(nullptr, pattern.get(), &result), FcPatternDestroy);
        return match ? open(library, match.get()) : nullptr;
    }
    void setPixelSize(unsigned size) {
        pixelSize = std::max(1u, size);
        FT_Set_Pixel_Sizes(primary, 0, pixelSize);
        for (const auto& [key, face] : faces) FT_Set_Pixel_Sizes(face, 0, pixelSize);
    }
    size_t fallbackFaceCount() const { return faces.size(); }
    FT_Face faceFor(uint32_t code) {
        if (FT_Get_Char_Index(primary, code)) return primary;
        if (auto it = choices.find(code); it != choices.end()) return it->second;
        Pattern pattern(FcPatternCreate(), FcPatternDestroy);
        Charset charset(FcCharSetCreate(), FcCharSetDestroy);
        if (pattern && charset) {
            FcCharSetAddChar(charset.get(), code);
            FcPatternAddCharSet(pattern.get(), FC_CHARSET, charset.get());
            FcPatternAddBool(pattern.get(), FC_SCALABLE, FcTrue);
            FcPatternAddInteger(pattern.get(), FC_WEIGHT, primary->style_flags & FT_STYLE_FLAG_BOLD ? FC_WEIGHT_BOLD : FC_WEIGHT_REGULAR);
            FcPatternAddInteger(pattern.get(), FC_SLANT, primary->style_flags & FT_STYLE_FLAG_ITALIC ? FC_SLANT_ITALIC : FC_SLANT_ROMAN);
            if (primary->family_name)
                FcPatternAddString(pattern.get(), FC_FAMILY, reinterpret_cast<const FcChar8*>(primary->family_name));
            FcConfigSubstitute(nullptr, pattern.get(), FcMatchPattern);
            FcDefaultSubstitute(pattern.get());
            FcResult result;
            FontSet matches(FcFontSort(nullptr, pattern.get(), FcTrue, nullptr, &result), FcFontSetDestroy);
            if (matches) for (int i = 0; i < matches->nfont; ++i) {
                auto* candidate = matches->fonts[i];
                FcCharSet* coverage = nullptr;
                if (FcPatternGetCharSet(candidate, FC_CHARSET, 0, &coverage) != FcResultMatch ||
                    !FcCharSetHasChar(coverage, code)) continue;
                FcChar8* path = nullptr; int index = 0;
                if (FcPatternGetString(candidate, FC_FILE, 0, &path) != FcResultMatch) continue;
                FcPatternGetInteger(candidate, FC_INDEX, 0, &index);
                const auto key = std::string(reinterpret_cast<const char*>(path)) + ':' + std::to_string(index);
                auto it = faces.find(key);
                FT_Face face = it == faces.end() ? open(library, candidate) : it->second;
                if (!face) continue;
                if (it == faces.end()) {
                    if (FT_Set_Pixel_Sizes(face, 0, pixelSize)) { FT_Done_Face(face); continue; }
                    faces.emplace(key, face);
                }
                // Fontconfig may report stale coverage; FreeType is authoritative.
                if (FT_Get_Char_Index(face, code)) return choices[code] = face;
            }
        }
        return choices[code] = primary; // A visible .notdef if no installed font covers it.
    }
    FT_GlyphSlot load(uint32_t code, FT_Int32 flags) {
        auto face = faceFor(code);
        if (FT_Load_Char(face, code, flags)) return nullptr;
        return face->glyph;
    }
};

inline uint8_t glyphCoverage(const FT_Bitmap& bitmap, unsigned row, unsigned col) {
    // FreeType pitch is signed; its magnitude may exceed width (MONO is packed).
    const auto* line = bitmap.buffer + static_cast<ptrdiff_t>(row) * bitmap.pitch;
    if (bitmap.pixel_mode == FT_PIXEL_MODE_MONO) return (line[col / 8] & (0x80 >> (col % 8))) ? 255 : 0;
    if (bitmap.pixel_mode == FT_PIXEL_MODE_GRAY) {
        const unsigned levels = bitmap.num_grays > 1 ? bitmap.num_grays - 1 : 255;
        return static_cast<uint8_t>(static_cast<unsigned>(line[col]) * 255 / levels);
    }
    if (bitmap.pixel_mode == FT_PIXEL_MODE_BGRA) return line[col * 4 + 3];
    return 0;
}
}
