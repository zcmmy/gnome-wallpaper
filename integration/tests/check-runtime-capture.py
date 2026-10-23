#!/usr/bin/env python3
"""Scene and video independent high-quality capture in a private GNOME session; no desktop mutations."""
from pathlib import Path
import os,shutil,subprocess,signal
r=Path(__file__).resolve().parents[2];t=r/'runtime/runtime-capture-test';out=r/'reports/hq-recapture'
out.mkdir(parents=True,exist_ok=True)
ext=t/'data/gnome-shell/extensions/wallpaperengine@waylandwe'
shutil.copytree(r/'gnome/extension',ext,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__'))
for ident in [os.environ['WALLPAPER_TEST_SCENE_A'],os.environ['WALLPAPER_TEST_SCENE_C']]:
 shutil.copytree(r/'wallpapers'/ident,t/'wallpapers'/ident,dirs_exist_ok=True)
shutil.copy2(r/'integration/tests/runtime-capture-driver.js',ext/'runtimeCaptureTest.js')
p=ext/'wallpaperExtension.js';s=p.read_text()+"\nimport {startTest} from './runtimeCaptureTest.js';\n";s=s.replace('        this._manager.start();','        this._manager.start();\n        GLib.idle_add(GLib.PRIORITY_DEFAULT,()=>{startTest(this);return GLib.SOURCE_REMOVE;});');p.write_text(s)
script=(r/'integration/tests/manager-session.sh.in').read_text().replace('manager-test','runtime-capture-test')
(t/'run-test.sh').write_text(script)
env=os.environ.copy();env.pop('WAYLAND_SOCKET',None)
before=subprocess.check_output(['dconf','dump','/org/gnome/'])
with (out/'integration.log').open('w') as log:
 p=subprocess.Popen(['bash',str(t/'run-test.sh')],env=env,stdout=log,stderr=log,start_new_session=True)
 try:p.wait(timeout=300)
 finally:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
text=(out/'integration.log').read_text()
assert 'RUNTIME-CAPTURE PASS' in text and 'RUNTIME-CAPTURE ERROR' not in text,text[-5000:]
assert before==subprocess.check_output(['dconf','dump','/org/gnome/']),'Actual desktop settings changed'
print('PASS: independent HQ scene/video capture and replacement; renderer PID/FPS unchanged, frames advance, actual desktop unchanged')
