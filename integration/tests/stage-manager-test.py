from pathlib import Path
import shutil
r=Path(__file__).resolve().parents[2];test=r/'runtime/manager-test';(test/'data/gnome-shell/extensions').mkdir(parents=True,exist_ok=True)
ext=test/'data/gnome-shell/extensions/wallpaperengine@waylandwe';shutil.copytree(r/'gnome/extension',ext,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git'))
lib=test/'wallpapers';lib.mkdir(exist_ok=True)
for ident in [os.environ['WALLPAPER_TEST_SCENE_A'],os.environ['WALLPAPER_TEST_SCENE_B']]:
 shutil.copytree(r/'wallpapers'/ident,lib/ident,dirs_exist_ok=True)
shutil.copytree(r/'wallpapers'/os.environ['WALLPAPER_TEST_SCENE_A'],lib/'capture-fixture',dirs_exist_ok=True)
(lib/'capture-fixture/static-background.png').unlink(missing_ok=True)
(lib/'capture-fixture/thumbnail.jpg').unlink(missing_ok=True)

shutil.copy2(r/'integration/tests/manager-test-driver.js',ext/'testDriver.js')
p=ext/'wallpaperExtension.js';s=p.read_text()+"\nimport {startTest} from './testDriver.js';\n";s=s.replace('        this._manager.start();',"        this._manager.start();\n        GLib.idle_add(GLib.PRIORITY_DEFAULT,()=>{startTest(this);return GLib.SOURCE_REMOVE;});");p.write_text(s)
script=(r/'integration/tests/manager-session.sh.in').read_text()
(r/'runtime/manager-test/run-test.sh').write_text(script)
print('Test staged')
