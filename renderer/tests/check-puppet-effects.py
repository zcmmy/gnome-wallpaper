#!/usr/bin/env python3
"""GPU regression: effect masks follow source UVs through a deformed puppet.

Uses a synthetic model, private compositor and temporary files. No Workshop
resources are embedded. --renderer permits checking an older runtime as well.
"""
import argparse
import json
import pathlib
import struct
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERTEX = '''uniform mat4 g_ModelViewProjectionMatrix;
attribute vec3 a_Position;
attribute vec2 a_TexCoord;
varying vec2 v_TexCoord;
void main() {
    gl_Position = g_ModelViewProjectionMatrix * vec4(a_Position, 1.0);
    v_TexCoord = a_TexCoord;
}
'''
FRAGMENTS = {
    'base': '''varying vec2 v_TexCoord;
void main() { gl_FragColor = v_TexCoord.x < 0.5 ? vec4(1,0,0,1) : vec4(0,1,0,1); }
''',
    'mask': '''uniform sampler2D g_Texture0;
varying vec2 v_TexCoord;
void main() {
    gl_FragColor = texSample2D(g_Texture0, v_TexCoord);
    if (v_TexCoord.x < 0.25) gl_FragColor.rgb = vec3(0,0,1);
}
''',
    'copy': '''uniform sampler2D g_Texture0;
varying vec2 v_TexCoord;
void main() { gl_FragColor = texSample2D(g_Texture0, v_TexCoord); }
''',
}


def puppet():
    # Mesh occupies only the right half of its 1000x800 image, but samples
    # the entire source UV square. An effect after deformation will miss it.
    data = bytearray(b'MDLV0015\0')
    data += struct.pack('<I', 4 * 80)
    for x, y, u, v in [(0,200,0,0), (400,200,1,0), (400,-200,1,1), (0,-200,0,1)]:
        vertex = [0.0] * 20
        vertex[0:3] = [x, y, 0]
        vertex[14] = 1
        vertex[18:20] = [u, v]
        data += struct.pack('<20f', *vertex)
    data += struct.pack('<I6H', 12, 0, 2, 1, 0, 3, 2)
    return data


def write_json(path, data):
    path.write_text(json.dumps(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--renderer', default=str(ROOT / 'renderer/scripts/run.sh'))
    args = parser.parse_args()
    import gi
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf
    with tempfile.TemporaryDirectory(prefix='wallpaper-puppet-test-') as directory:
        root = pathlib.Path(directory)
        scene = root / 'scene'
        for name in ('models', 'materials', 'shaders', 'effects'):
            (scene / name).mkdir(parents=True)
        (scene / 'models/puppet.mdl').write_bytes(puppet())
        write_json(scene / 'project.json', {'type': 'scene', 'file': 'scene.json', 'title': 'Puppet effect regression'})
        write_json(scene / 'models/image.json', {'material': 'materials/base.json', 'puppet': 'models/puppet.mdl'})
        for name, fragment in FRAGMENTS.items():
            (scene / f'shaders/{name}.vert').write_text(VERTEX)
            (scene / f'shaders/{name}.frag').write_text(fragment)
            write_json(scene / f'materials/{name}.json', {'passes': [{
                'shader': name, 'blending': 'translucent', 'cullmode': 'normal',
                **({'textures': ['util/white']} if name == 'base' else {}),
            }]})
            write_json(scene / f'effects/{name}.json', {'passes': [{'material': f'materials/{name}.json'}]})
        for effects in ([], ['mask'], ['mask', 'copy']):
            document = {
                'camera': {'center': '0 0 -1', 'eye': '0 0 0', 'up': '0 1 0'},
                'general': {'orthogonalprojection': {'width': 1920, 'height': 1080},
                            'bloom': False, 'clearcolor': '0 0 0', 'clearenabled': True},
                'objects': [{'id': 1, 'name': 'puppet', 'image': 'models/image.json',
                             'origin': '960 540 0', 'size': '1000 800',
                             'effects': [{'file': f'effects/{name}.json', 'id': i + 10, 'visible': True}
                                         for i, name in enumerate(effects)]}],
            }
            write_json(scene / 'scene.json', document)
            out = root / f'{len(effects)}.png'
            diagnostics = root / f'log-{len(effects)}'
            subprocess.run(['python3', str(ROOT / 'gnome/extension/captureWorker.py'),
                            '--quality', 'standard', '--renderer', args.renderer,
                            '--assets', str(ROOT / 'assets'), '--scene', str(scene),
                            '--output', str(out), '--diagnostics', str(diagnostics)], check=True)
            log = (diagnostics / 'renderer.log').read_text()
            assert 'vertices=4' in log and 'indices=6' in log, log[-4000:]
            assert 'Cannot compile' not in log and 'failed to build' not in log, log[-4000:]
            image = GdkPixbuf.Pixbuf.new_from_file(str(out))
            pixels = image.get_pixels()
            def rgb(x, y):
                i = y * image.get_rowstride() + x * image.get_n_channels()
                return tuple(pixels[i:i+3])
            expected = (0, 0, 255) if effects else (255, 0, 0)
            assert rgb(1000, 500) == expected, (effects, 'source mask misplaced', rgb(1000, 500), expected)
            assert rgb(1280, 500) == (0, 255, 0), (effects, 'puppet UVs lost', rgb(1280, 500))
            assert rgb(800, 500) == (0, 0, 0), (effects, 'mesh drawn as an undeformed quad', rgb(800, 500))
            print(f'PASS: puppet source UV mask with {len(effects)} effect passes')


if __name__ == '__main__':
    main()
