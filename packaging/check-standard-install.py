#!/usr/bin/env python3
"""Observe GNOME's ZIP installer in a separate data directory and session bus."""
import json,mmap,os,pathlib,subprocess,tempfile,zipfile
with tempfile.TemporaryDirectory(prefix='wallpaper-standard-install-') as tmp:
 root=pathlib.Path(tmp);env=os.environ.copy();env.pop('DBUS_SESSION_BUS_ADDRESS',None)
 for name in ['DATA','CONFIG','CACHE','STATE','RUNTIME']:
  path=root/name.lower();path.mkdir(mode=0o700);env['XDG_'+name+('_DIR' if name=='RUNTIME' else '_HOME')]=str(path)
 uuid='wallpaper-install-probe@example.invalid';archive=root/'probe.zip'
 def install(value,force=False):
  with zipfile.ZipFile(archive,'w') as z:
   for name,content,mode in [('metadata.json',json.dumps({'uuid':uuid,'name':'Install probe','description':'Isolated installer behavior','shell-version':['48']}),0o644),('extension.js','export default class Extension {}',0o644),('backend-probe',value,0o755)]:
    info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(0o100000|mode)<<16;z.writestr(info,content)
  args=['dbus-run-session','--','gnome-extensions','install']+(['--force'] if force else [])+[str(archive)]
  subprocess.run(args,env=env,check=True,capture_output=True)
 install('first');program=root/'data/gnome-shell/extensions'/uuid/'backend-probe'
 with program.open('rb') as file:
  mapped=mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ);before=program.stat().st_ino
  install('next!',True)
  print(json.dumps({'executable_preserved':bool(program.stat().st_mode&0o111),'inode_replaced':program.stat().st_ino!=before,'mapped_old_bytes':mapped[:].decode(),'installed_bytes':program.read_text(),'automatic_backup':len(list(program.parent.parent.iterdir()))>1}))
  mapped.close()
