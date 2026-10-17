#!/usr/bin/env python3
"""Run the prepared-background regression in a private GNOME session."""
import json, pathlib, subprocess, tempfile, shlex
root = pathlib.Path(__file__).resolve().parents[2]
report = root / 'reports/static-background'
report.mkdir(exist_ok=True)
script = (root / 'integration/tests/nested-gnome.sh').read_text()
script = script.replace('cd "$(dirname "$(readlink -f "$0")")/../.."', 'cd ' + shlex.quote(str(root)))
script = script.replace('integration/tests/nested-test-driver.js', 'integration/tests/static-background-driver.js')
script = script.replace('fps 30', 'fps 15').replace('runtime/nested/', 'runtime/static-background-test/')
script = script.replace('wallpaper-adapter-test', 'wallpaper-static-test')
script = script.replace('gsettings set org.gnome.shell disable-user-extensions false', 'gsettings set org.gnome.shell disable-user-extensions false\ngsettings set org.gnome.shell welcome-dialog-last-shown-version "48.0"')
script = '\n'.join(line for line in script.splitlines() if 'sed -i' not in line or '--screenshot' not in line) + '\n'
with tempfile.NamedTemporaryFile(mode='w', suffix='.sh') as launcher:
    launcher.write(script); launcher.flush()
    with (report / 'integration.log').open('w') as log:
        subprocess.run(['bash', launcher.name], cwd=root, stdout=log, stderr=subprocess.STDOUT, timeout=65, check=True)
text = (report / 'integration.log').read_text()
assert not any(x in text for x in ['STATIC-TEST ERROR', 'JS ERROR', 'Clutter-CRITICAL', 'assertion']), text[-5000:]
entries = [json.loads(line.split('STATIC-TEST ', 1)[1]) for line in text.splitlines() if 'STATIC-TEST {' in line]
assert [e['label'] for e in entries] == ['started', 'mid-transition', 'repeat-transition', 'stopped-static', 'restarted', 'complete'], entries
assert all(e['fps'] == 15 for e in entries)
assert len({entries[i]['pid'] for i in range(3)}) == 1
assert entries[4]['pid'] != entries[0]['pid']
(report / 'integration.json').write_text(json.dumps(entries, indent=2))
print('PASS: prepared still at startup, mid-swipe, repeated switch, stop and restart; 15 FPS; no runtime screenshot')
