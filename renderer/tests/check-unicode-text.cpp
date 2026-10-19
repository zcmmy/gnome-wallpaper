#include "WallpaperEngine/Render/UnicodeText.h"
#include "WallpaperEngine/Render/FontFallback.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <vector>
using namespace WallpaperEngine::Render;
std::vector<uint32_t> decode(const std::string& s) {
    std::vector<uint32_t> out;
    for (size_t i = 0; i < s.size();) out.push_back(nextUtf8Codepoint(s, i));
    return out;
}
int main(int argc, char** argv) {
    assert((decode("A中文かな한글éΩЖ😀") == std::vector<uint32_t>{65,0x4e2d,0x6587,0x304b,0x306a,0xd55c,0xae00,0xe9,0x3a9,0x416,0x1f600}));
    for (const auto& bad : {std::string("\xc0\xaf"),std::string("\xe0\x80\x80"),std::string("\xed\xa0\x80"),
         std::string("\xf4\x90\x80\x80"),std::string("\xf0\x80\x80\x80"),std::string("\xe4\xb8"),std::string("\x80")}) {
        auto codes=decode(bad+"Z"); assert(codes.front()==0xfffd && codes.back()=='Z');
        for (auto c:codes) assert(c==0xfffd || c=='Z');
    }
    assert((decode(std::string("\xe4Z"))==std::vector<uint32_t>{0xfffd,'Z'}));
    assert(argc == 3); // Explicit fixture font paths; no user's font configuration.
    auto* config=FcConfigCreate();
    assert(FcConfigAppFontAddFile(config,reinterpret_cast<const FcChar8*>(argv[1])));
    assert(FcConfigAppFontAddFile(config,reinterpret_cast<const FcChar8*>(argv[2])));
    assert(FcConfigSetCurrent(config));
    FT_Library library=nullptr; FT_Face primary=nullptr;
    assert(!FT_Init_FreeType(&library)); assert(!FT_New_Face(library,argv[1],0,&primary));
    assert(!FT_Select_Charmap(primary,FT_ENCODING_UNICODE));
    assert(FT_Get_Char_Index(primary,0x4e2d)==0);
    assert(!FT_Load_Char(primary,0x4e2d,FT_LOAD_RENDER)); // The old success check accepts .notdef.
    {
        FontFallback fonts(library,primary); fonts.setPixelSize(40);
        for (auto code:decode("中文漢字かなカナ한글한국어éΩЖ😀")) {
            auto* face=fonts.faceFor(code); assert(face && FT_Get_Char_Index(face,code)!=0);
            auto* slot=fonts.load(code,FT_LOAD_RENDER); assert(slot && slot->bitmap.rows>0);
            bool ink=false;
            for(unsigned y=0;y<slot->bitmap.rows;y++) for(unsigned x=0;x<slot->bitmap.width;x++)
                ink |= glyphCoverage(slot->bitmap,y,x)>0;
            assert(ink);
        }
        assert(fonts.faceFor('A')==primary); // Existing authored Latin glyphs are preserved.
        auto* cjk=fonts.faceFor(0x4e2d); assert(cjk!=primary);
        assert(cjk->num_faces>1); // TTC collection supported.
        const auto count=fonts.fallbackFaceCount();
        for(int repeat=0;repeat<100;repeat++) assert(fonts.faceFor(0x4e2d)==cjk);
        assert(fonts.fallbackFaceCount()==count);
        fonts.setPixelSize(80); auto* glyph=fonts.load(0xd55c,FT_LOAD_RENDER);
        assert(glyph && glyph->face->size->metrics.y_ppem==80);
        assert(fonts.load(0x10ffff,FT_LOAD_RENDER)); // Unsupported scalar remains safe.
    }
    unsigned char bits[]={0x81,0x40}; FT_Bitmap bitmap{};
    bitmap.buffer=bits;bitmap.width=8;bitmap.rows=2;bitmap.pitch=1;bitmap.pixel_mode=FT_PIXEL_MODE_MONO;
    assert(glyphCoverage(bitmap,0,0)==255 && glyphCoverage(bitmap,0,1)==0 && glyphCoverage(bitmap,1,1)==255);
    bitmap.buffer=bits+1;bitmap.pitch=-1;
    assert(glyphCoverage(bitmap,0,1)==255 && glyphCoverage(bitmap,1,0)==255);
    FT_Done_Face(primary);FT_Done_FreeType(library);
    FcConfigDestroy(config);FcFini();
    std::cout << "PASS: strict UTF-8, CJK/Latin/Greek/Cyrillic glyphs, TTC, fallback cache, resize, missing glyph and signed bitmap pitch\n";
}
