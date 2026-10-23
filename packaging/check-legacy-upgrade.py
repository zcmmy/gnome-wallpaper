#!/usr/bin/env python3
"""Exercise legacy upgrade/rollback against an isolated real GSettings backend."""
import argparse,importlib.util,json,os,pathlib,shutil,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('archive',type=pathlib.Path);p.add_argument('--inside',type=pathlib.Path);a=p.parse_args()
if not a.inside:
    with tempfile.TemporaryDirectory(prefix='wallpaper-upgrade-') as tmp:
        root=pathlib.Path(tmp);env=os.environ.copy();env.pop('DBUS_SESSION_BUS_ADDRESS',None);env.pop('GSETTINGS_BACKEND',None);env.update(GIO_USE_VFS='local',GVFS_DISABLE_FUSE='1')
        for kind in ['DATA','CONFIG','CACHE','STATE','RUNTIME']:
            path=root/kind.lower();path.mkdir(mode=0o700);env['XDG_'+kind+('_DIR' if kind=='RUNTIME' else '_HOME')]=str(path)
        subprocess.run(['dbus-run-session','--','/usr/bin/python3',__file__,str(a.archive.absolute()),'--inside',str(root)],env=env,check=True)
else:
    spec=importlib.util.spec_from_file_location('installer',ROOT/'packaging/install.py');i=importlib.util.module_from_spec(spec);spec.loader.exec_module(i)
    dest=a.inside/i.UUID;dest.mkdir();shutil.copy2(ROOT/'gnome/extension/metadata.json',dest/'metadata.json');shutil.copytree(ROOT/'gnome/extension/schemas',dest/'schemas')
    subprocess.run(['glib-compile-schemas',str(dest/'schemas')],check=True)
    env=dict(os.environ,GSETTINGS_SCHEMA_DIR=str(dest/'schemas'));os.environ['GSETTINGS_SCHEMA_DIR']=str(dest/'schemas')
    schema='org.gnome.shell.extensions.wallpaperengine'
    def set_(key,value):subprocess.run(['gsettings','set',schema,key,value],env=env,check=True)
    def get(key):return subprocess.check_output(['gsettings','get',schema,key],env=env,text=True).strip()
    set_('wallpaperengine-path',json.dumps('/legacy program/renderer'));set_('engine',"'wallpaperengine'");set_('enabled','true')
    result=i.install(a.archive.absolute(),dest,True);backup=pathlib.Path(result['backup'])
    assert backup.with_name(backup.name+'.settings.json').stat().st_mode&0o777==0o600
    set_('wallpaperengine-path',json.dumps(str(dest/'backend/linux-x86_64/bin/renderer')))
    set_('library-root',json.dumps(str(a.inside/'managed library')));set_('fps','24')
    subprocess.run(['/usr/bin/python3',str(ROOT/'packaging/install.py'),'--yes','--destination',str(dest),'--restore',str(backup)],env=env,check=True,stdout=subprocess.DEVNULL)
    assert get('wallpaperengine-path')=="'/legacy program/renderer'"
    assert get('library-root')==repr(str(a.inside/'managed library')) and get('fps')=='24' and get('enabled')=='false'
    assert not (dest/'package-manifest.json').exists()
    print('PASS: legacy upgrade/rollback restores only the backend entry and retains managed library/FPS/static mode')
