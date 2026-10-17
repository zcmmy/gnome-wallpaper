#include "WallpaperEngine/Input/PointerCoordinates.h"
#include "WallpaperEngine/Api/CommandDispatcher.h"
#include <cassert>
#include <cmath>
#include <iostream>
using WallpaperEngine::Api::CommandDispatcher;
int main() {
    using namespace WallpaperEngine::Input;
    for (double scale : {1., 1.25, 1.5, 2.}) {
        for (auto point : {glm::dvec2{0,0}, glm::dvec2{.5,.5}, glm::dvec2{1,1}, glm::dvec2{.1,.9}}) {
            auto n = logicalPointer(point.x*960, point.y*540, 960, 540);
            assert(n && *n == point);
            glm::ivec2 fb{960*scale, 540*scale};
            auto pixels = framebufferPointer(*n, fb);
            assert(std::abs(pixels.x/fb.x-point.x)<1e-12);
            assert(std::abs(1-pixels.y/fb.y-point.y)<1e-12);
        }
    }
    assert(!logicalPointer(1,1,0,540));
    assert(!logicalPointer(1,1,960,0));
    assert(*logicalPointer(-1,1000,960,540)==glm::dvec2(0,1));
    const std::string valid = R"({"id":1,"cmd":"pointer","args":{"x":0.1,"y":0.9,"left":true,"right":false,"active":true}})";
    assert(CommandDispatcher::parse(valid).command);
    auto j=nlohmann::json::parse(valid);
    for(auto key:{"x","y"}) {
        auto bad=j; bad["args"][key]=1.1; assert(!CommandDispatcher::parse(bad.dump()).command);
        bad["args"][key]=-0.1; assert(!CommandDispatcher::parse(bad.dump()).command);
        bad["args"][key]="nan"; assert(!CommandDispatcher::parse(bad.dump()).command);
        bad["args"].erase(key); assert(!CommandDispatcher::parse(bad.dump()).command);
    }
    for(auto key:{"left","right","active"}) {
        auto bad=j; bad["args"][key]=1; assert(!CommandDispatcher::parse(bad.dump()).command);
        bad["args"].erase(key); assert(!CommandDispatcher::parse(bad.dump()).command);
    }
    std::cout << "PASS: pointer scaling 100/125/150/200%, degenerate geometry and IPC validation\n";
}
