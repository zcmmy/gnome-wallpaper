#include "WallpaperEngine/Render/CaptureResampler.h"
#include <iostream>
#include <stdexcept>
using namespace WallpaperEngine::Render::Capture;
void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
std::vector<uint8_t> gray(std::initializer_list<int> values){std::vector<uint8_t> v;for(auto x:values)for(int c=0;c<3;c++)v.push_back(x);return v;}
int main(){
 auto original=gray({0,40,80,120,160,200});
 check(resampleRgb(original,3,2,3,2)==original,"1:1 image shifted");
 check(resampleRgb(original,3,2,3,2,1,0,1,0)==gray({200,160,120,80,40,0}),"reversed UV lost edge pixel");
 check(resampleRgb(gray({0,255}),2,1,1,1)==gray({128}),"2:1 average wrong");
 auto fractional=resampleRgb(gray({0,255,0,255}),4,1,3,1);
 check(fractional==gray({64,128,191}),"fractional footprint average wrong");
 check(resampleRgb(gray({0,255}),2,1,4,1)==gray({0,64,191,255}),"bilinear centers wrong");
 check(resampleRgb(gray({10,20,30,40}),4,1,2,1,.25,.75)==gray({20,30}),"UV crop misaligned");
 check(resampleRgb(gray({10,110}),2,1,2,1,-.5,1.5)==gray({10,110}),"outside clamping wrong");
 check(resampleRgb(gray({73}),1,1,7,5)==std::vector<uint8_t>(7*5*3,73),"single pixel edge failed");
 check(resampleRgb(original,3,2,1,1)==gray({100}),"two-axis area average failed");
 // Aliasing fixture: 2x2 checkerboard cells must retain mean energy at 4:1 reduction.
 std::vector<uint8_t> checker(64*64*3);
 for(int y=0;y<64;y++)for(int x=0;x<64;x++)for(int c=0;c<3;c++)checker[(y*64+x)*3+c]=((x+y)%2)*255;
 auto small=resampleRgb(checker,64,64,16,16);
 check(std::all_of(small.begin(),small.end(),[](uint8_t v){return v==128;}),"checkerboard aliases instead of averaging");
 for(int mode=0;mode<3;mode++){
  bool rejected=false;try{
   if(mode==0)resampleRgb({},1,1,1,1);
   if(mode==1)resampleRgb(original,3,2,0,1);
   if(mode==2)resampleRgb(original,3,2,1,1,std::numeric_limits<double>::quiet_NaN());
  }catch(const std::invalid_argument&){rejected=true;}check(rejected,"invalid capture accepted");
 }
 std::cout<<"PASS: identity, crop, UV flips, area minification, centered interpolation, clamping, checkerboard antialiasing, invalid buffers\n";
}
