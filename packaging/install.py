#!/usr/bin/env python3
"""One-entry, atomic full extension installer. User data is never installed or removed."""
import argparse,ctypes,hashlib,json,os,pathlib,platform,shutil,stat,subprocess,tempfile,time,uuid,zipfile
UUID='wallpaperengine@waylandwe'

def verify(directory):
    manifest=json.loads((directory/'package-manifest.json').read_text())
    if manifest.get('uuid')!=UUID or manifest.get('format')!=1 or manifest.get('backend_protocol')!=1:raise ValueError('Unsupported package identity/protocol')
    actual={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()}
    if actual!=set(manifest['files'])|{'package-manifest.json'}:raise ValueError('Package has missing or unlisted files')
    for name,record in manifest['files'].items():
        path=pathlib.PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe manifest path')
        p=directory/name
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Package checksum mismatch: '+name)
        if stat.S_IMODE(p.stat().st_mode)!=record['mode']:raise ValueError('Package mode mismatch: '+name)
    return manifest

def extract(archive,directory):
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate archive entry')
        if sum(p.file_size for p in z.infolist())>4*1024**3:raise ValueError('Package too large')
        for info in z.infolist():
            name=pathlib.PurePosixPath(info.filename);mode=info.external_attr>>16
            if name.is_absolute() or '..' in name.parts or '\\' in info.filename or stat.S_ISLNK(mode) or not stat.S_ISREG(mode):raise ValueError('Unsafe ZIP entry')
            path=directory/name;path.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info) as src,path.open('xb') as dst:shutil.copyfileobj(src,dst)
            path.chmod(0o755 if mode&0o111 else 0o644)
    return verify(directory)

def preflight(stage):
    if platform.machine()!='x86_64':raise ValueError('This package requires x86_64')
    os_release=pathlib.Path('/etc/os-release').read_text()
    if 'ID=debian' not in os_release or 'VERSION_ID="13"' not in os_release:raise ValueError('This build supports Debian 13 only')
    for command in ['gjs','gnome-shell','glib-compile-schemas','gdbus','dbus-run-session','python3']:
        if not shutil.which(command):raise ValueError('Missing GNOME host component: '+command)
    shell_version=subprocess.check_output(['gnome-shell','--version'],text=True).split()[-1]
    if shell_version.split('.')[0]!='48':raise ValueError('This build requires GNOME 48')
    subprocess.run(['gjs','-c',"imports.gi.versions.Gtk='4.0'; imports.gi.versions.Adw='1'; void imports.gi.Gtk; void imports.gi.Adw;"],check=True)
    subprocess.run(['/usr/bin/python3','-c',"import gi; gi.require_version('GdkPixbuf','2.0'); from gi.repository import GdkPixbuf"],check=True)
    subprocess.run([str(stage/'backend/linux-x86_64/bin/renderer'),'--check'],check=True,stdout=subprocess.DEVNULL)

def owned_tasks(destination):
    prefix=str(destination)+'/';found=[]
    for proc in pathlib.Path('/proc').glob('[0-9]*'):
        try:
            if proc.stat().st_uid!=os.getuid():continue
            args=(proc/'cmdline').read_bytes().decode(errors='replace').split('\0')
            if any(value.startswith(prefix+'backend/') or value==prefix+'captureWorker.py' for value in args):found.append(proc.name)
        except (OSError,ProcessLookupError):pass
    return found

def stop_owned_tasks(destination):
    if not destination.exists() or not (destination/'schemas/gschemas.compiled').exists():return
    env=dict(os.environ,GSETTINGS_SCHEMA_DIR=str(destination/'schemas'))
    schema='org.gnome.shell.extensions.wallpaperengine'
    subprocess.run(['gsettings','set',schema,'enabled','false'],env=env,check=True)
    # Existing Shell code reports its owned process/task teardown. Do not signal unrelated PIDs.
    for _ in range(100):
        value=subprocess.check_output(['gsettings','get',schema,'runtime-status'],env=env,text=True).strip()
        try:
            import ast
            state=json.loads(ast.literal_eval(value))
        except (ValueError,SyntaxError):state={}
        if not state.get('pid') and not state.get('capturing') and not owned_tasks(destination):return
        time.sleep(.1)
    raise ValueError('Wallpaper tasks have not stopped. Original installation retained.')

def exchange(stage,destination):
    if not destination.exists():stage.rename(destination);return None
    if destination.is_symlink():raise ValueError('Installation destination must not be a symlink')
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.renameat2(-100,os.fsencode(stage),-100,os.fsencode(destination),2):raise OSError(ctypes.get_errno(),'Atomic install failed')
    backup=destination.parent/('.'+UUID+'.backup-'+uuid.uuid4().hex)
    try:stage.rename(backup)
    except OSError:
        # Restore the previous directory before the staging cleanup can run.
        if libc.renameat2(-100,os.fsencode(stage),-100,os.fsencode(destination),2):
            error=RuntimeError('Backup rename failed; preserved previous files at '+str(stage));error.preserve_stage=True;raise error
        raise
    return backup

def install(archive,destination,desktop=True):
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=pathlib.Path(tempfile.mkdtemp(prefix='.wallpaper-install-',dir=destination.parent))
    preserve_stage=False
    try:
        manifest=extract(archive,stage);preflight(stage)
        # Compile in staging, never truncate a schema mmap in the active installation.
        subprocess.run(['glib-compile-schemas','--strict',str(stage/'schemas')],check=True)
        if desktop:stop_owned_tasks(destination)
        backup=exchange(stage,destination)
        return {'installed':str(destination),'version':manifest['version'],'backup':str(backup) if backup else None,'reload':'next login','user_data':'preserved'}
    except Exception as error:
        preserve_stage=getattr(error,'preserve_stage',False);raise
    finally:
        if stage.exists() and not preserve_stage:shutil.rmtree(stage)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=pathlib.Path,nargs='?');p.add_argument('--destination',type=pathlib.Path);p.add_argument('--yes',action='store_true');p.add_argument('--isolated',action='store_true',help='test destination only; never touches session settings');p.add_argument('--restore',type=pathlib.Path)
    args=p.parse_args();standard=pathlib.Path(os.environ.get('XDG_DATA_HOME',str(pathlib.Path.home()/'.local/share')))/'gnome-shell/extensions'/UUID
    destination=args.destination.absolute() if args.destination else standard
    if args.isolated and (not args.destination or destination==standard):p.error('--isolated requires a separate explicit test destination')
    if not args.yes:
        if input('Install/update wallpaper program, stopping its playback if needed? User data will be retained. [y/N] ').lower()!='y':return
    if args.restore:
        backup=args.restore.absolute()
        if backup.parent!=destination.parent or not backup.name.startswith('.'+UUID+'.backup-') or backup.is_symlink():raise ValueError('Invalid rollback directory')
        if json.loads((backup/'metadata.json').read_text())['uuid']!=UUID:raise ValueError('Invalid rollback identity')
        if not args.isolated:stop_owned_tasks(destination)
        print(json.dumps({'restored':str(destination),'backup':str(exchange(backup,destination))}));return
    if not args.archive:p.error('Select a full extension ZIP')
    print(json.dumps(install(args.archive,destination,not args.isolated),ensure_ascii=False))
if __name__=='__main__':main()
