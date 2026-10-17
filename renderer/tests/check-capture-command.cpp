#include "WallpaperEngine/Api/CommandDispatcher.h"
#include <cassert>
#include <iostream>
int main() {
    using WallpaperEngine::Api::CommandDispatcher;
    auto request=nlohmann::json{{"id",1},{"cmd","screenshot"},{"args",{{"path","/tmp/capture.png"}}}};
    assert(CommandDispatcher::parse(request.dump()).command);
    for (const auto& path : {std::string(""),std::string("relative.png"),std::string("/tmp/out.jpg"),std::string("/tmp/x\0.png",11),std::string(4097,'x')}) {
        request["args"]["path"]=path;assert(!CommandDispatcher::parse(request.dump()).command);
    }
    for (const auto& value : {nlohmann::json(nullptr),nlohmann::json(12),nlohmann::json(true)}) {
        request["args"]["path"]=value;assert(!CommandDispatcher::parse(request.dump()).command);
    }
    request["args"]=nlohmann::json::object();assert(!CommandDispatcher::parse(request.dump()).command);
    std::cout << "PASS: runtime screenshot request path validation\n";
}
