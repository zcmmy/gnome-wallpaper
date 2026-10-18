#include "WallpaperEngine/Render/Shaders/SourceCompatibility.h"
#include <cassert>
#include <iostream>
using WallpaperEngine::Render::Shaders::repairLegacyEffectSource;
int main () {
    const std::string unrelated = "#endif\nfloat outside; outside ? other : names;\n";
    assert (repairLegacyEffectSource (unrelated) == unrelated);
    const auto bars = repairLegacyEffectSource (
	"float i_DCorrectingFactor;\r\n#if DEFORMITY == 3\r\n#ifdef INNER\r\n#endif\r\n#endif\r\n#endif\r\n");
    assert (bars.find ("#ifdef INNER\r\n#endif\r\n#endif\r\n") != std::string::npos);
    assert (bars.find ("// Legacy audio-bars surplus #endif") != std::string::npos);
    const auto oriented = repairLegacyEffectSource (
        "varying vec2 v_TexCoord; varying float i_DCorrectingFactor; uniform float u_BarCount; "
        "void main() { v_TexCoord = v_TexCoord.yx; gl_FragColor = vec4(v_TexCoord, 0., 1.); }");
    assert (oriented.find ("varying vec2 v_TexCoord;") != std::string::npos);
    assert (oriented.find ("vec2 lwe_LocalBarUV = v_TexCoord;") != std::string::npos);
    assert (oriented.find ("lwe_LocalBarUV = lwe_LocalBarUV.yx") != std::string::npos);
    assert (repairLegacyEffectSource (oriented) == oriented);
    const auto frame = repairLegacyEffectSource ("float outside; outside ? inSmooth : outSmooth;");
    assert (frame.find ("(outside != 0.0) ? inSmooth : outSmooth") != std::string::npos);
    const std::string spectrum = "vec3 drawSence(vec2 uv) { float x = g_AudioSpectrum64Left[barID / 4][barID % 4]; "
				 "vec4 col; col.rgb = mix(u_userNewColor, col, step(0., x)); return col; }";
    const auto repaired = repairLegacyEffectSource (spectrum);
    assert (repaired.find ("g_AudioSpectrum64Left[clamp(int(barID), 0, 63)]") != std::string::npos);
    assert (repaired.find ("mix(u_userNewColor, col.rgb, step") != std::string::npos);
    assert (repaired.find ("return col.rgb;") != std::string::npos);
    assert (repairLegacyEffectSource (repaired) == repaired);
    assert (repairLegacyEffectSource ("g_AudioSpectrum64Left[id / 4][id % 4]") ==
	    "g_AudioSpectrum64Left[id / 4][id % 4]");
    std::cout << "PASS: legacy shader signatures, nested directives, CRLF and unrelated source preservation\n";
}
