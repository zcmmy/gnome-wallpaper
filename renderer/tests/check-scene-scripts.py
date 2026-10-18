#!/usr/bin/env python3
"""Integration regression on a private compositor (no desktop settings touched)."""
import json
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
# No Workshop source/assets are included in this synthetic fixture.
SCRIPT = '''
export function init(value) {
    const later = thisScene.getLayer("later");
    if (!later || later.name !== "later" || later.id !== 2) throw Error("later layer missing during init");
    if (later.getParent().id !== 3) throw Error("non-drawing parent missing");
    if (thisScene.getLayer("absent") !== undefined) throw Error("missing layer must be undefined");
    if (engine.isRunningInEditor() !== false) throw Error("incorrect editor mode");
    if (later !== thisScene.getLayer(2)) throw Error("unstable layer identity");
    thisLayer.marker = 42;
    const oldLog = console.log; console.log = () => {}; console.log = oldLog;
    later.visible = false;
    if (thisScene.getLayer(2).visible !== false) throw Error("write was only stored in a JS wrapper");
    thisScene.getLayer("label").text = "UPDATED";
    return value;
}
let checked = false;
export function update(value) {
    if (thisLayer.name !== "controller" || thisLayer.marker !== 42) throw Error("wrong callback layer or lost custom fields");
    if (!checked) {
        if (thisScene.getLayer("label").text !== "UPDATED") throw Error("cross-layer text lost");
        console.log("SCENE-SCRIPT-REGRESSION-PASS");
        checked = true;
    }
    return value;
}
'''

def main():
    with tempfile.TemporaryDirectory(prefix='wallpaper-script-test-') as directory:
        root = pathlib.Path(directory)
        scene = root / 'scene'
        scene.mkdir()
        (scene / 'project.json').write_text(json.dumps({'type': 'scene', 'file': 'scene.json', 'title': 'Script regression'}))
        document = {
            'camera': {'center': '0 0 -1', 'eye': '0 0 0', 'up': '0 1 0'},
            'general': {'orthogonalprojection': {'width': 1920, 'height': 1080}, 'bloom': False,
                        'clearcolor': '0 0 0', 'clearenabled': True},
            'objects': [
                {'id': 1, 'name': 'controller', 'origin': '0 0 0', 'visible': {'value': True, 'script': SCRIPT}},
                {'id': 2, 'name': 'later', 'origin': '0 0 0', 'parent': 3},
                {'id': 3, 'name': 'parent', 'origin': '0 0 0'},
                {'id': 4, 'name': 'label', 'origin': '960 540 0', 'text': '', 'pointsize': 80},
            ],
        }
        (scene / 'scene.json').write_text(json.dumps(document))
        output = root / 'capture.png'
        subprocess.run(['python3', str(ROOT / 'gnome/extension/captureWorker.py'),
                        '--renderer', str(ROOT / 'renderer/scripts/run.sh'), '--assets', str(ROOT / 'assets'),
                        '--scene', str(scene), '--output', str(output), '--diagnostics', str(root / 'log')], check=True)
        log = (root / 'log/renderer.log').read_text()
        assert 'SCENE-SCRIPT-REGRESSION-PASS' in log, log[-6000:]
        assert 'threw' not in log and 'evaluation rejected' not in log, log[-6000:]
        import gi
        gi.require_version('GdkPixbuf', '2.0')
        from gi.repository import GdkPixbuf
        image = GdkPixbuf.Pixbuf.new_from_file(str(output))
        pixels = image.get_pixels()
        bright = sum(pixels[y * image.get_rowstride() + x * image.get_n_channels()] > 128
                     for y in range(image.get_height()) for x in range(image.get_width()))
        assert bright > 1000, 'Initially empty text never became visible'
        print('PASS: deferred init, groups, parent/name/id, shared property writes and initially empty text rendering')

if __name__ == '__main__':
    main()
