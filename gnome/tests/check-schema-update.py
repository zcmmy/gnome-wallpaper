#!/usr/bin/env python3
import pathlib,tempfile,subprocess,shutil,json,os
r=pathlib.Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='wallpaper-schema-test-') as tmp:
 t=pathlib.Path(tmp);old=t/'installed';new=t/'new'
 for path,value in [(old,1),(new,2)]:
  (path/'schemas').mkdir(parents=True)
  (path/'metadata.json').write_text(json.dumps({'uuid':'wallpaperengine@waylandwe'}))
  (path/'extension.js').write_text('export default class {}')
  extra=''.join(f'<key name="extra-{i}" type="s"><default>"long-value-{i}"</default></key>' for i in range(40)) if value==2 else ''
  (path/'schemas/test.gschema.xml').write_text(f'<schemalist><schema id="org.wallpaper.Test" path="/org/wallpaper/Test/">{extra}<key name="monitor-index" type="i"><default>{value}</default></key></schema></schemalist>')
  subprocess.run(['glib-compile-schemas','--strict',str(path/'schemas')],check=True)
 script=t/'test.js'
 script.write_text("""import Gio from 'gi://Gio';
const dir=ARGV[0],installer=ARGV[1],source=ARGV[2];
const oldSource=Gio.SettingsSchemaSource.new_from_directory(dir+'/schemas',null,false);
const old=new Gio.Settings({settings_schema:oldSource.lookup('org.wallpaper.Test',false)});
if(old.get_int('monitor-index')!==1)throw new Error('old setup failed');
Gio.Subprocess.new(['python3',installer,source,dir],0).wait_check(null);
if(old.get_int('monitor-index')!==1 || !old.settings_schema.has_key('monitor-index'))throw new Error('old mapped schema corrupted');
const freshSource=Gio.SettingsSchemaSource.new_from_directory(dir+'/schemas',null,false);
const fresh=new Gio.Settings({settings_schema:freshSource.lookup('org.wallpaper.Test',false)});
if(fresh.get_int('monitor-index')!==2 || !fresh.settings_schema.has_key('extra-39'))throw new Error('new schema unavailable');
print('PASS: live old GSettings mapping preserved; new instance sees updated schema');
""")
 env=os.environ.copy();env['GSETTINGS_BACKEND']='memory'
 before=(old/'schemas/gschemas.compiled').stat().st_ino
 subprocess.run(['gjs','-m',str(script),str(old),str(r/'gnome/scripts/install-extension.py'),str(new)],env=env,check=True)
 after=(old/'schemas/gschemas.compiled').stat().st_ino
 assert before!=after
 (new/'schemas/test.gschema.xml').write_text('<invalid>')
 bad=subprocess.run(['python3',str(r/'gnome/scripts/install-extension.py'),str(new),str(old)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 assert bad.returncode!=0 and (old/'schemas/gschemas.compiled').stat().st_ino==after
 print('PASS: invalid update leaves existing extension untouched')
