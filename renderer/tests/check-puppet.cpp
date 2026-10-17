#include "WallpaperEngine/Render/Objects/PuppetModel.h"
#include <cassert>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
using WallpaperEngine::Render::Objects::PuppetModel;
template <typename T> void append (std::vector<char> &out, T v) {
    const auto *p = reinterpret_cast<const char *> (&v);
    out.insert (out.end (), p, p + sizeof (v));
}
void string (std::vector<char> &out, const std::string &value) {
    out.insert (out.end (), value.begin (), value.end ());
    out.push_back (0);
}
std::vector<char> fixture (bool metadata, bool truncated = false) {
    std::vector<char> out;
    string (out, "MDLV0015");
    // Legacy stride-80 triangle, independent of any third-party wallpaper.
    append<uint32_t> (out, 240);
    for (int i = 0; i < 3; ++i) {
	float vertex[20] = {};
	vertex[0] = i == 1;
	vertex[1] = i == 2;
	vertex[14] = 1;
	auto *p = reinterpret_cast<char *> (vertex);
	out.insert (out.end (), p, p + sizeof (vertex));
    }
    append<uint32_t> (out, 6);
    for (uint16_t i = 0; i < 3; ++i)
	append (out, i);
    string (out, "MDLS0004");
    append<uint32_t> (out, 0);
    append<uint32_t> (out, 2);
    out.push_back (0);
    for (int i = 0; i < 2; ++i) {
	append<uint32_t> (out, 1);
	append<int32_t> (out, i - 1);
	append<uint32_t> (out, 64);
	for (int j = 0; j < 16; ++j)
	    append<float> (out, j % 5 == 0 ? 1.f : 0.f);
	if (truncated && i == 1) {
	    out.insert (out.end (), {'b', 'a', 'd'});
	    return out;
	}
	string (out, metadata ? "{\"tm\":100,\"tp\":\"-nan(ind)\"}" : "");
	string (out, metadata ? "bone " + std::to_string (i) : "");
    }
    return out;
}
int main (int argc, char **argv) {
    for (bool metadata : {false, true}) {
	std::string error;
	auto model = PuppetModel::parse (fixture (metadata), error);
	assert (model && model->positions.size () == 3 && model->bones.size () == 2);
	assert (model->bones[0].parent == -1 && model->bones[1].parent == 0);
	std::vector<glm::mat4> skin;
	model->evaluateSkinning ({}, 0, skin);
	std::vector<glm::vec3> positions;
	model->skinPositions (skin, positions);
	assert (positions == model->positions);
    }
    std::string error;
    auto truncated = PuppetModel::parse (fixture (true, true), error);
    assert (truncated && truncated->bones.empty ());
    if (argc > 1) {
	std::ifstream file (argv[1], std::ios::binary);
	const std::vector<char> data ((std::istreambuf_iterator<char> (file)), {});
	auto model = PuppetModel::parse (data, error);
	assert (model && model->bones.size () == 54 && model->clips.size () == 5);
	assert (model->findClip (1597) && model->findClip (1846));
	std::vector<glm::mat4> skin;
	std::vector<glm::vec3> a, b;
	const std::vector<PuppetModel::ActiveLayer> layers{{model->findClip (1597), 1, 1}};
	model->evaluateSkinning (layers, 0, skin);
	model->skinPositions (skin, a);
	model->evaluateSkinning (layers, 1, skin);
	model->skinPositions (skin, b);
	assert (a != b);
	std::cout << "PASS: local Mika rig has 54 bones, 5 clips and animated vertices\n";
    }
    std::cout << "PASS: puppet metadata strings, empty legacy strings and truncated metadata\n";
}
