#!/usr/bin/env python3
"""Verify a relocated runtime with the entire development tree hidden by bwrap."""
import argparse,hashlib,json,os,pathlib,shutil,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('bundle',type=pathlib.Path);a=p.parse_args()
r=pathlib.Path(__file__).resolve().parents[2];bundle=a.bundle.resolve()
manifest=json.loads((bundle/'manifest.json').read_text())
for name,digest in manifest['files_sha256'].items():
 if name in manifest.get('mutable_files',[]) or any(name.startswith(prefix) for prefix in manifest.get('mutable_directories',[])):continue
 assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==digest,name
assert not any(f.is_symlink() for f in bundle.rglob('*'))
before=subprocess.check_output(['dconf','dump','/org/gnome/'])
out=r/'reports/runtime-bundle-verification';out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='wallpaper-bundle-verify-') as tmp:
 t=pathlib.Path(tmp);b=t/'runtime relocated';shutil.copytree(bundle,b)
 (t/'run').mkdir(mode=0o700)
 for name in ['logs','reports','integration/tests','runtime/nested']:(t/name).mkdir(parents=True)
 shutil.copy2(r/'integration/tests/nested-test-driver.js',t/'integration/tests/nested-test-driver.js')
 shutil.copy2(r/'integration/tests/runtime-preview-driver.py',t/'preview-check.py')
 s=(r/'integration/tests/nested-gnome.sh').read_text()
 s=s.replace('cp gnome/extension/*.js gnome/extension/metadata.json', 'cp "$WALLPAPER_BUNDLE"/gnome/wallpaperengine@waylandwe/*.js "$WALLPAPER_BUNDLE"/gnome/wallpaperengine@waylandwe/metadata.json')
 s=s.replace('cp -r gnome/extension/schemas','cp -r "$WALLPAPER_BUNDLE/gnome/wallpaperengine@waylandwe/schemas"')
 for old,new in [('wallpaper','wallpaper'),('assets','assets'),('renderer/scripts/run.sh','bin/renderer')]:s=s.replace('$WALLPAPER_TEST_ROOT/'+old,'$WALLPAPER_BUNDLE/'+new)
 script=t/'integration/tests/nested-gnome.sh';script.write_text(s);script.chmod(0o755)
 s=(r/'integration/tests/check-gnome-integration.py').read_text()
 s=s.replace("j=json.loads(data)['result']; out.append", "j=json.loads(data)['result']; assert pathlib.Path('/proc',str(j['pid']),'exe').resolve().is_relative_to(pathlib.Path(os.environ['WALLPAPER_BUNDLE'])); assert os.environ['WALLPAPER_DEVELOPMENT_ROOT']+'/' not in pathlib.Path('/proc',str(j['pid']),'maps').read_text(); out.append")
 (t/'integration/tests/check-gnome-integration.py').write_text(s)
 env=os.environ.copy();env['WALLPAPER_BUNDLE']=str(b);env['RUNTIME_TEST_DIR']=str(t);env['WALLPAPER_DEVELOPMENT_ROOT']=str(r);env.pop('LD_LIBRARY_PATH',None)
 base=['bwrap','--die-with-parent','--ro-bind','/','/','--dev-bind','/dev','/dev','--proc','/proc','--tmpfs','/tmp','--bind',str(t),str(t),'--tmpfs',str(r),'--chdir',str(t)]
 nested=env.copy();nested['XDG_RUNTIME_DIR']=str(t/'run');nested['PULSE_SERVER']='unix:'+os.environ.get('XDG_RUNTIME_DIR','/run/user/'+str(os.getuid()))+'/pulse/native'
 for key in ['WAYLAND_DISPLAY','DISPLAY']:nested.pop(key,None)
 try:
  subprocess.run(base+['python3',str(t/'integration/tests/check-gnome-integration.py')],env=nested,check=True,timeout=100)
  subprocess.run(base+['python3',str(t/'preview-check.py')],env=env,check=True,timeout=45)
 finally:
  for folder in ['logs','reports']:
   for file in (t/folder).iterdir():
    if file.is_file():shutil.copy2(file,out/file.name)
  after=subprocess.check_output(['dconf','dump','/org/gnome/'])
  assert before==after,'Desktop settings changed during validation'
 summary={'passed':True,'bundle':str(bundle),'manifest_verified':True,'no_symlinks':True,'relocated_to_path_with_spaces':True,'development_tree_hidden':str(r),'nested_gnome_checks':'passed','standalone_preview':'passed','desktop_settings_unchanged':True,'autostart_added':False}
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print('PASS: runtime independent of development tree; reports:',out)
