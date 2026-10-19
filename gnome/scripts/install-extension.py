#!/usr/bin/env python3
"""Stage and atomically replace an extension; never change settings or enable it."""
import argparse,ctypes,datetime,json,os,pathlib,shutil,subprocess,tempfile

def install(source,destination):
    source=pathlib.Path(source).resolve();destination=pathlib.Path(destination).absolute()
    if source==destination:raise ValueError('Source and destination must differ')
    metadata=json.loads((source/'metadata.json').read_text())
    if metadata.get('uuid')!='wallpaperengine@waylandwe':raise ValueError('Unexpected extension UUID')
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=pathlib.Path(tempfile.mkdtemp(prefix='.wallpaper-stage-',dir=destination.parent))
    backup=None;exchanged=False
    try:
        (stage/'schemas').mkdir()
        for file in source.glob('*.js'):shutil.copy2(file,stage/file.name)
        shutil.copy2(source/'libraryWorker.py',stage/'libraryWorker.py') if (source/'libraryWorker.py').exists() else None
        if (source/'captureWorker.py').exists():shutil.copy2(source/'captureWorker.py',stage/'captureWorker.py')
        for name in ['common','helpers','backend','licenses','resources']:
            if (source/name).is_dir():shutil.copytree(source/name,stage/name,symlinks=False)
        for name in ['VERSION','package-manifest.json']:
            if (source/name).is_file():shutil.copy2(source/name,stage/name)
        shutil.copy2(source/'metadata.json',stage/'metadata.json')
        for name in ['LICENSE','NOTICE.md']:
            notice=source/name
            if not notice.exists():notice=source.parents[1]/name
            if notice.exists():shutil.copy2(notice,stage/name)
        for file in (source/'schemas').glob('*.gschema.xml'):shutil.copy2(file,stage/'schemas'/file.name)
        subprocess.run(['glib-compile-schemas','--strict',str(stage/'schemas')],check=True)
        if not (stage/'extension.js').exists() or not (stage/'schemas/gschemas.compiled').exists():raise ValueError('Incomplete extension')
        if destination.exists():
            # GSettings maps gschemas.compiled. NEVER truncate or rewrite its inode.
            # Exchange complete directories so existing mappings retain old bytes.
            libc=ctypes.CDLL(None,use_errno=True)
            libc.renameat2.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
            libc.renameat2.restype=ctypes.c_int
            if libc.renameat2(-100,os.fsencode(stage),-100,os.fsencode(destination),2):
                raise OSError(ctypes.get_errno(),'Atomic exchange failed; original extension remains intact')
            exchanged=True
            backup=destination.parent/('.wallpaper-backup-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            stage.rename(backup)
        else:stage.rename(destination)
        return {'installed':str(destination),'backup':str(backup) if backup else None,'enabled':False,'settings_changed':False}
    finally:
        if stage.exists() and not exchanged:shutil.rmtree(stage)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=pathlib.Path);parser.add_argument('destination',type=pathlib.Path)
    args=parser.parse_args();print(json.dumps(install(args.source,args.destination),ensure_ascii=False))
