#pragma once
#include <regex>
#include <sstream>
#include <string>

namespace WallpaperEngine::Render::Shaders {
// Some Workshop effects ship GLSL-like sources with legacy HLSL expressions.
// Keep these repairs signature-gated: unrelated shaders must still fail normally.
inline std::string repairLegacyEffectSource (std::string source) {
    if (source.find ("i_DCorrectingFactor") != std::string::npos &&
	source.find ("#if DEFORMITY == 3") != std::string::npos) {
	// The shared Audio Bars vertex template contains a surplus closing #endif.
	// Preserve all balanced directives and line numbers (including CRLF input).
	std::istringstream input (source);
	std::ostringstream output;
	std::string line;
	int depth = 0;
	const std::regex opening (R"(^\s*#\s*(if|ifdef|ifndef)\b.*)");
	const std::regex closing (R"(^\s*#\s*endif\b.*)");
	while (std::getline (input, line)) {
	    std::string directive = line;
	    if (!directive.empty () && directive.back () == '\r')
		directive.pop_back ();
	    if (std::regex_match (directive, opening))
		++depth;
	    else if (std::regex_match (directive, closing)) {
		if (depth == 0)
		    line = "// Legacy audio-bars surplus #endif";
		else
		    --depth;
	    }
	    output << line << '\n';
	}
	source = output.str ();
    }
    // Audio Bars orientation variants mutate UVs in main(), which is legal in
    // their original shader dialect but not for a GLSL fragment input. Keep the
    // varying interface intact and transform a local copy inside this template.
    if (source.find ("i_DCorrectingFactor") != std::string::npos &&
        source.find ("u_BarCount") != std::string::npos &&
        source.find ("gl_FragColor") != std::string::npos &&
        source.find ("lwe_LocalBarUV") == std::string::npos) {
        const std::regex mainDecl (R"(void\s+main\s*\(\s*\)\s*\{)");
        std::smatch match;
        if (std::regex_search (source, match, mainDecl)) {
            const size_t body = match.position () + match.length ();
            source = source.substr (0, body) + "\nvec2 lwe_LocalBarUV = v_TexCoord;\n" +
                std::regex_replace (source.substr (body), std::regex (R"(\bv_TexCoord\b)"), "lwe_LocalBarUV");
        }
    }
    // Frame Builder stores its condition as a 0/1 float (implicit bool in HLSL).
    if (source.find ("float outside") != std::string::npos)
	source = std::regex_replace (source, std::regex (R"(\boutside\s*\?\s*inSmooth\s*:\s*outSmooth)"),
				     "(outside != 0.0) ? inSmooth : outSmooth");
    // A legacy circular spectrum uses packed vec4 indexing on a float[64].
    // Collapse the row/column pair to the original bin and cast the float loop ID.
    const std::regex packed (
	R"((g_AudioSpectrum64(?:Left|Right))\[\s*([A-Za-z_]\w*)\s*/\s*4\s*\]\[\s*\2\s*%\s*4\s*\])");
    if (std::regex_search (source, packed) && source.find ("vec3 drawSence(vec2 uv)") != std::string::npos) {
	source = std::regex_replace (source, packed, "$1[clamp(int($2), 0, 63)]");
	// Explicit HLSL vector truncation for the same legacy function.
	source = std::regex_replace (source, std::regex (R"(mix\(u_userNewColor,\s*col,\s*step)"),
				     "mix(u_userNewColor, col.rgb, step");
	source = std::regex_replace (source, std::regex (R"(return\s+col\s*;)"), "return col.rgb;");
    }
    return source;
}
} // namespace WallpaperEngine::Render::Shaders
