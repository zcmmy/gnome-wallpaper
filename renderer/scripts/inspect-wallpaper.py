#!/usr/bin/env python3
"""Read a Wallpaper Engine package without modifying or executing its contents."""
import hashlib, json, struct
from pathlib import Path
root = Path(__file__).resolve().parents[2]
path = root / 'wallpaper/scene.pkg'
b = path.read_bytes(); pos = 0

def u32():
    global pos
    if pos + 4 > len(b): raise ValueError('truncated package')
    v = struct.unpack_from('<I', b, pos)[0]; pos += 4
    return v

def take(n):
    global pos
    if n > len(b) - pos: raise ValueError('truncated package')
    v = b[pos:pos+n]; pos += n
    return v
header = take(u32()).decode(); count = u32(); entries = {}
if count > 100000: raise ValueError('unexpected entry count')
for _ in range(count):
    name = take(u32()).decode(); off = u32(); size = u32()
    entries[name] = (off, size)
base = pos

def read(name):
    off, size = entries[name]; start = base + off
    if start + size > len(b): raise ValueError('invalid entry bounds')
    return b[start:start+size]

textures = []
for name in entries:
    if not name.endswith('.tex'): continue
    t = read(name)
    if not t.startswith(b'TEXV0005\0TEXI0001\0'): continue
    fmt, flags, tw, th, w, h, _ = struct.unpack_from('<7I', t, 18)
    item = dict(path=name, format=fmt, flags=flags, texture_size=[tw,th], image_size=[w,h],
                container=t[46:54].decode(), image_count=struct.unpack_from('<I',t,55)[0])
    # For TEXB0003, skip every stored mip payload before interpreting the animation table.
    if t[46:55] == b'TEXB0003\0':
        p = 63; decoded_bytes = 0; mip_count = 0
        for image in range(item['image_count']):
            n = struct.unpack_from('<I',t,p)[0]; p += 4
            if not 0 < n <= 32: raise ValueError('invalid mip count')
            for mip in range(n):
                mw,mh,comp,usize,csize = struct.unpack_from('<5I',t,p); p += 20
                if p+csize > len(t): raise ValueError('invalid texture payload')
                decoded_bytes += usize if comp else csize; p += csize; mip_count += 1
        item.update(decoded_mip_bytes=decoded_bytes, mip_count=mip_count)
        if flags & 4:
            item['animation_version'] = t[p:p+8].decode()
            frames = struct.unpack_from('<I',t,p+9)[0]; p += 13
            item['frames'] = frames
            if item['animation_version'] == 'TEXS0003':
                item['frame_size'] = list(struct.unpack_from('<2I',t,p)); p += 8
            if p+32*frames > len(t): raise ValueError('truncated animation')
            durations = [struct.unpack_from('<f',t,p+32*i+4)[0] for i in range(frames)]
            item['animation_duration_seconds'] = sum(durations)
    textures.append(item)
scene = json.loads(read('scene.json'))
report = dict(package=header, file_count=count, sha256=hashlib.sha256(b).hexdigest(),
              object_count=len(scene['objects']), textures=textures,
              missing_common_model_refs=sorted({o['image'] for o in scene['objects'] if o.get('image') not in entries}))
print(json.dumps(report, ensure_ascii=False, indent=2))
