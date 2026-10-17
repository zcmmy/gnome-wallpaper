#include <cstring>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include "WallpaperEngine/Data/Parsers/TextureParser.h"
#include "WallpaperEngine/Data/Utils/BinaryReader.h"
#include "WallpaperEngine/Data/Utils/MemoryStream.h"
using namespace WallpaperEngine::Data::Utils;
using namespace WallpaperEngine::Data::Parsers;
void u32(std::string& b,uint32_t v){for(int i=0;i<4;i++)b.push_back(char(v>>(i*8)));}
void magic(std::string& b,const char* s){b.append(s,8);b.push_back(0);}
std::string fixture(uint32_t flags,uint32_t size){
 std::string b;magic(b,"TEXV0005");magic(b,"TEXI0001");
 for(auto v:{0u,flags,1920u,1080u,1920u,1080u,0u})u32(b,v);
 magic(b,"TEXB0004");
 for(auto v:{1u,0xffffffffu,0u,1u,1920u,1080u,0u,0u,size})u32(b,v);
 b+="0123456789abcdef";return b;
}
auto parse(const std::string& b){auto buf=std::make_unique<char[]>(b.size());std::memcpy(buf.get(),b.data(),b.size());BinaryReader reader(std::make_shared<MemoryStream>(std::move(buf),b.size()));return TextureParser::parse(reader);}
int main(){
 auto t=parse(fixture(32,16));auto m=t->images.at(0).at(0);
 if(m->compression!=0||m->uncompressedSize!=16||std::memcmp(m->uncompressedData.get(),"0123456789abcdef",16))throw std::runtime_error("raw video sentinel decoded incorrectly");
 for(auto b:{fixture(32,99),fixture(32,0xffffffffu),fixture(0,16)}){bool rejected=false;try{parse(b);}catch(...){rejected=true;}if(!rejected)throw std::runtime_error("invalid payload accepted");}
 std::cout<<"PASS: TEXB0004 raw video sentinel, byte preservation, payload bounds and non-video rejection\n";
}
