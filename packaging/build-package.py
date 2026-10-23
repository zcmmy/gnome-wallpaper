#!/usr/bin/env python3
"""Assemble a program-only, platform-specific extension. Never install or copy resources."""
import argparse,gzip,hashlib,importlib.util,json,os,pathlib,platform,re,shutil,subprocess,sys,tempfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'integration/scripts'))
from runtime_notices import collect_notices,PRIVATE_LIBRARY_PACKAGES
UUID='wallpaperengine@waylandwe'
# Host ABI and graphics dispatch/driver boundaries. Everything else in ldd's closure is private.
HOST=re.compile(r'^(ld-linux|lib(c|m|pthread|dl|rt|resolv|nss_[\w]+)\.so|lib(EGL|GL|GLX|GLdispatch|OpenGL|GLESv[12]|vulkan|OpenCL|cuda|nvidia[^.]*|drm[^.]*|gbm|wayland-[^.]+)\.so)')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def run(*args,**kw):return subprocess.check_output(args,text=True,**kw).strip()
def check_source_snapshot(repo):
    forbidden={'assets','wallpapers','wallpaper','deps','build','dist','logs'}
    entries=run('git','-C',str(repo),'ls-tree','-r','HEAD').splitlines()
    for entry in entries:
        info,name=entry.split('\t',1)
        if name.split('/')[0] in forbidden or name.startswith('docs/internal/'):
            raise ValueError('Private/generated path in source snapshot: '+name)
        if info.startswith('120000'):
            target=run('git','-C',str(repo),'show','HEAD:'+name)
            normalized=os.path.normpath(str(pathlib.PurePosixPath(name).parent/target))
            if pathlib.PurePosixPath(target).is_absolute() or normalized=='..' or normalized.startswith('../'):
                raise ValueError('Machine-specific or escaping source symlink: '+name)

def check_package_checkout(repo):
    inputs=['renderer/source','gnome/extension','packaging','integration/scripts','third_party',
            'Makefile','VERSION','LICENSE','NOTICE.md','docs']
    if run('git','-C',str(repo),'status','--porcelain','--untracked-files=normal','--',*inputs):
        raise ValueError('Commit package inputs before packaging so the corresponding source matches the installed files')

def resolve_sysroot():
    candidate=ROOT/'deps/sysroot/usr'
    if candidate.is_dir():return candidate.resolve()
    if (ROOT/'deps').exists() or (ROOT/'deps').is_symlink():
        raise ValueError('Configured deps/sysroot/usr is missing; repair the local toolchain before packaging')
    return pathlib.Path('/usr')

def check_build_checkout(home):
    if home.resolve()!=(ROOT/'renderer/source').resolve():
        raise ValueError('Build belongs to a different checkout; package from that checkout or rebuild here')

def source_identity(output):
    cache=(output.parent/'CMakeCache.txt').read_text()
    home=pathlib.Path(re.search(r'^CMAKE_HOME_DIRECTORY:INTERNAL=(.+)$',cache,re.M)[1])
    check_build_checkout(home)
    repo=pathlib.Path(run('git','-C',str(home),'rev-parse','--show-toplevel'))
    return {'commit':run('git','-C',str(repo),'rev-parse','HEAD'),'repository':'https://github.com/zcmmy/gnome-wallpaper',
            'compiler':run('c++','--version').splitlines()[0],'configuration':'Release', 'source_root':repo,
            'renderer_tree':run('git','-C',str(repo),'rev-parse','HEAD:renderer/source'),
            'cmake_flags':{key:re.search(r'^'+key+r':[^=]+=(.*)$',cache,re.M)[1] for key in ['CMAKE_BUILD_TYPE','CMAKE_C_FLAGS','CMAKE_CXX_FLAGS']}}
def package_identity(path,soname,sysroot):
    if sysroot != pathlib.Path('/usr') and path.is_relative_to(sysroot):
        package=PRIVATE_LIBRARY_PACKAGES.get(soname)
        if not package:raise ValueError('Unmapped private input: '+soname)
        copyright=sysroot/'share/doc'/package/'copyright'
        changelog=gzip.open(sysroot/'share/doc'/package/'changelog.Debian.gz','rt').readline()
        match=re.match(r'(\S+) \(([^)]+)\)',changelog)
        if not match:raise ValueError('Cannot identify source version: '+soname)
        source,source_version=match.groups()
        pins=dict(line.strip().rsplit('=',1) for line in (ROOT/'deps/packages.txt').read_text().splitlines() if '=' in line)
        version=pins[package]
    else:
        query=subprocess.run(['dpkg-query','-S',str(path)],capture_output=True,text=True)
        if query.returncode:query=subprocess.run(['dpkg-query','-S','*/'+path.name],capture_output=True,text=True)
        package=query.stdout.split(': ')[0].splitlines()[0]
        fields=run('dpkg-query','-W','-f=${Version}\t${source:Package}\t${source:Version}',package).split('\t')
        version,source,source_version=fields;package=package.split(':')[0]
        copyright=pathlib.Path('/usr/share/doc')/package/'copyright'
    if not copyright.is_file():raise ValueError('Missing notice: '+package)
    return {'package':package,'version':version,'source_package':source,'source_version':source_version,
            'source_url':'https://snapshot.debian.org/package/'+source+'/'+source_version+'/', 'copyright':copyright}
def build(args):
    if platform.machine()!='x86_64':raise ValueError('Only linux-x86_64 is currently supported')
    output=args.build_dir.resolve()/'output';sysroot=resolve_sysroot()
    env=dict(os.environ,LD_LIBRARY_PATH=f'{output}:{sysroot}/lib/x86_64-linux-gnu:{sysroot}/lib')
    linked=run('ldd',str(output/'linux-wallpaperengine'),env=env)
    if 'not found' in linked:raise ValueError(linked)
    libraries={n:pathlib.Path(p).resolve() for n,p in re.findall(r'^\s*(\S+) => (\S+) \(',linked,re.M)}
    out=args.output.absolute();out.mkdir(parents=True,exist_ok=False)
    identity=source_identity(output);source_repo=identity.pop('source_root')
    check_source_snapshot(source_repo)
    check_package_checkout(source_repo)
    identity['cmake_flags']={k:v.replace(str(source_repo),'<SOURCE>').replace(str((ROOT/'deps').resolve()),'<DEPS>') for k,v in identity['cmake_flags'].items()}
    if run('git','-C',str(source_repo),'status','--porcelain','--','renderer/source'):
        raise ValueError('Commit renderer sources before archiving corresponding source')
    stamp=json.loads((args.build_dir/'backend-build.json').read_text())
    if stamp.get('format')!=1 or stamp['renderer_tree']!=identity['renderer_tree'] or any(sha(output/name)!=digest for name,digest in stamp['outputs'].items()):
        raise ValueError('Backend build provenance mismatch; run make package-backend')
    version=(ROOT/'VERSION').read_text().strip()
    # Header/protocol source inputs contribute compiled code even without a shared object.
    source_inputs=[]
    for package in ['libglm-dev','wayland-protocols']:
        fields=run('dpkg-query','-W','-f=${Version}\t${source:Package}\t${source:Version}',package).split('\t') if sysroot==pathlib.Path('/usr') else None
        if fields:
            binary_version,source,source_version=fields
        else:
            line=gzip.open(sysroot/'share/doc'/package/'changelog.Debian.gz','rt').readline()
            source,source_version=re.match(r'(\S+) \(([^)]+)\)',line).groups()
            pins=dict(line.strip().rsplit('=',1) for line in (ROOT/'deps/packages.txt').read_text().splitlines() if '=' in line)
            binary_version=pins[package]
        source_inputs.append({'package':package,'version':binary_version,'source_package':source,'source_version':source_version})
    with tempfile.TemporaryDirectory(prefix='wallpaper-package-') as temp:
        stage=pathlib.Path(temp);backend=stage/'backend/linux-x86_64'
        for folder in ['bin','lib']: (backend/folder).mkdir(parents=True)
        ext=ROOT/'gnome/extension'
        for p in ext.glob('*'):
            if p.is_file() and p.suffix in ['.js','.py','.json']:shutil.copy2(p,stage/p.name)
        metadata=json.loads((stage/'metadata.json').read_text());metadata['shell-version']=['48']
        (stage/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
        for name in ['common','helpers','schemas']:shutil.copytree(ext/name,stage/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','gschemas.compiled'))
        for name in ['LICENSE','NOTICE.md','VERSION']:shutil.copy2(ROOT/name,stage/name)
        subprocess.run(['glib-compile-schemas','--strict',str(stage/'schemas')],check=True)
        shutil.copy2(output/'linux-wallpaperengine',backend/'bin/linux-wallpaperengine')
        collected={n:p for n,p in libraries.items() if not HOST.match(n)}
        collect_notices(ROOT,sysroot,output,stage/'licenses',{n:p for n,p in collected.items() if n in PRIVATE_LIBRARY_PACKAGES or n=='liblinux-wallpaperengine-lib.so'})
        records=[];host=[];common=set()
        for name,path in sorted(libraries.items()):
            if HOST.match(name):host.append(name);continue
            shutil.copy2(path,backend/'lib'/name)
            record={'soname':name,'sha256':sha(path)}
            if name=='liblinux-wallpaperengine-lib.so':record['project']=identity
            else:
                package=package_identity(path,name,sysroot);copyright=package.pop('copyright')
                target=stage/'licenses/packages'/package['package'];target.mkdir(parents=True,exist_ok=True)
                shutil.copy2(copyright,target/'copyright')
                common.update(re.findall(r'/usr/share/common-licenses/([\w.+-]+)',copyright.read_text()))
                record.update(package)
            records.append(record)
        for name in sorted(common):
            name=name.rstrip('.')
            p=pathlib.Path('/usr/share/common-licenses')/name
            if not p.is_file() and name in ['GPL-2.0','GPL-3.0','LGPL-2.0','LGPL-3.0']:
                p=p.with_name(name.removesuffix('.0'))
            if not p.is_file():raise ValueError('Missing license text: '+name)
            shutil.copy2(p,stage/'licenses/common'/name)
        requirements=[]
        for p in [backend/'bin/linux-wallpaperengine',*(backend/'lib').iterdir()]:
            requirements+=re.findall(r'\bGLIBC_(\d+\.\d+)\b',run('readelf','--version-info',str(p)))
        minimum=max(requirements,key=lambda s:tuple(map(int,s.split('.'))))
        manifest={'format':1,'protocol':1,'version':version,'platform':'linux-x86_64','capabilities':['scene','video','capture-hq','pointer','spectrum','set-fps'],
                  'channel':'development','host':{'distribution':'Debian 13','gnome':'48','glibc_minimum':minimum,'libraries':host,
                          'commands':['gjs','gnome-shell','dbus-run-session','gdbus','python3'],
                          'python_modules':['gi'],'gi_modules':['Gtk-4.0','Adw-1','GdkPixbuf-2.0'],'font_resources':'Host Fontconfig configuration and fonts (CJK fonts needed for CJK text)'},
                  'renderer_build':identity,'libraries':records,'source_inputs':source_inputs}
        (backend/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        shutil.copy2(ROOT/'packaging/renderer-launcher.py',backend/'bin/renderer');(backend/'bin/renderer').chmod(0o755)
        # Probe loading using only private libs + declared host ABI; no scene/audio is initialized.
        subprocess.run([str(backend/'bin/renderer'),'--check'],check=True,stdout=subprocess.DEVNULL)
        files={str(p.relative_to(stage)):{'sha256':sha(p),'mode':0o755 if os.access(p,os.X_OK) else 0o644} for p in sorted(stage.rglob('*')) if p.is_file()}
        (stage/'package-manifest.json').write_text(json.dumps({'format':1,'uuid':UUID,'version':version,'backend_protocol':1,'files':files},indent=2)+'\n')
        archive=out/f'gnome-wallpaper-{version}-linux-x86_64.shell-extension.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in sorted(stage.rglob('*')):
                if p.is_file():
                    info=zipfile.ZipInfo(p.relative_to(stage).as_posix(),(1980,1,1,0,0,0));info.create_system=3
                    info.external_attr=(0o100755 if os.access(p,os.X_OK) else 0o100644)<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
        shutil.copy2(backend/'manifest.json',out/'backend-manifest.json')
        subprocess.run(['git','-C',str(source_repo),'archive','--format=tar.gz','--output='+str(out/'renderer-corresponding-source.tar.gz'),identity['commit']],check=True)
    shutil.copy2(ROOT/'packaging/install.py',out/'install.py')
    shutil.copy2(ROOT/'docs/FULL-PACKAGE.md',out/'INSTALL.md')
    shutil.copy2(ROOT/'docs/PACKAGING-VALIDATION.md',out/'PACKAGING-VALIDATION.md')
    shutil.copy2(ROOT/'packaging/fetch-sources.py',out/'fetch-sources.py')
    (out/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(out.iterdir()) if p.is_file()))
    print(json.dumps({'output':str(out),'private_libraries':len(records),'host_libraries':len(host),'glibc_minimum':minimum,'archive_bytes':archive.stat().st_size}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build-dir',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True)
    build(p.parse_args())
