#!/usr/bin/env python3
"""Generate a tiny MJPEG AVI test pattern without external media or encoders."""
import json,pathlib,struct,sys
import gi
gi.require_version('GdkPixbuf','2.0')
from gi.repository import GdkPixbuf
folder=pathlib.Path(sys.argv[1]);folder.mkdir(parents=True,exist_ok=True)
width,height,rate,frames=320,180,15,30

def chunk(tag,data):
    return tag+struct.pack('<I',len(data))+data+(b'\0' if len(data)%2 else b'')
def listing(tag,data):
    return chunk(b'LIST',tag+data)
images=[]
for i in range(frames):
    pix=GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,False,8,width,height)
    pix.fill(0x336699ff if i%rate<rate//2 else 0xcc6633ff)
    if i==0:pix.savev(str(folder/'static-background.png'),'png',[],[])
    ok,image=pix.save_to_bufferv('jpeg',[],[]);assert ok;images.append(bytes(image))
size=max(map(len,images))
avih=struct.pack('<14I',1000000//rate,size*rate,0,0x10,frames,0,1,size,width,height,0,0,0,0)
strh=struct.pack('<4s4sIHHIIIIIIIIhhhh',b'vids',b'MJPG',0,0,0,0,1,rate,0,frames,size,0xffffffff,0,0,0,width,height)
strf=struct.pack('<IiiHH4sIiiII',40,width,height,1,24,b'MJPG',width*height*3,0,0,0,0)
header=listing(b'hdrl',chunk(b'avih',avih)+listing(b'strl',chunk(b'strh',strh)+chunk(b'strf',strf)))
video=b'';index=b'';offset=4
for image in images:
    frame=chunk(b'00dc',image);index+=struct.pack('<4sIII',b'00dc',0x10,offset,len(image));video+=frame;offset+=len(frame)
(folder/'clip.avi').write_bytes(chunk(b'RIFF',b'AVI '+header+listing(b'movi',video)+chunk(b'idx1',index)))
(folder/'project.json').write_text(json.dumps({'type':'video','file':'clip.avi','title':'Synthetic video test'}))
