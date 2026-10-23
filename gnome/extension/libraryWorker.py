#!/usr/bin/env python3
"""Short-lived file operations; never starts a wallpaper renderer."""
import ctypes,fcntl,json,os,pathlib,shutil,sys,tempfile

def validate(folder):
    if folder.is_symlink() or not folder.is_dir():raise ValueError('请选择普通壁纸目录，不支持符号链接')
    project=folder/'project.json'
    if not project.is_file() or project.stat().st_size>1048576:raise ValueError('缺少有效的 project.json')
    data=json.loads(project.read_text())
    kind=str(data.get('type','')).lower()
    if kind not in ('scene','video'):raise ValueError('目前支持 scene 和 video 壁纸')
    entry=pathlib.Path(str(data.get('file','')))
    if entry.is_absolute() or '..' in entry.parts or not entry.parts:raise ValueError('无效的壁纸入口路径')
    if not (folder/entry).is_file() and not (kind=='scene' and (folder/'scene.pkg').is_file()):raise ValueError('壁纸资源不完整：找不到入口文件或 scene.pkg')
    for base,dirs,files in os.walk(folder,followlinks=False):
        for name in dirs+files:
            path=pathlib.Path(base)/name
            if path.is_symlink() or not (path.is_dir() or path.is_file()):raise ValueError('壁纸目录包含链接或特殊文件，未导入')
    return data

def import_wallpapers(root,source):
    source=pathlib.Path(source).absolute()
    if source.is_symlink():raise ValueError('不支持符号链接目录')
    source=source.resolve()
    if source==root or source in root.parents:raise ValueError('不能将壁纸库自身或其上级目录导入壁纸库')
    candidates=[source] if (source/'project.json').is_file() else sorted(p for p in source.iterdir() if p.is_dir() and (p/'project.json').is_file())
    if not candidates:raise ValueError('未找到 project.json；请选择壁纸目录或包含这些目录的文件夹')
    result={'imported':[],'skipped':[],'errors':[]}
    for folder in candidates:
        try:
            ident=folder.name
            if ident.startswith('.') or not ident:raise ValueError('不支持隐藏目录名称')
            if (root/ident).exists():result['skipped'].append(ident);continue
            validate(folder)
            # Stage beside the library: partial copies never appear in its catalog.
            stage=pathlib.Path(tempfile.mkdtemp(prefix='.wallpaper-import-',dir=root.parent))
            try:
                target=stage/ident;shutil.copytree(folder,target)
                validate(target)
                if (root/ident).exists():raise ValueError('目标目录已存在，未覆盖')
                libc=ctypes.CDLL(None,use_errno=True)
                libc.renameat2.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
                libc.renameat2.restype=ctypes.c_int
                if libc.renameat2(-100,os.fsencode(target),-100,os.fsencode(root/ident),1):
                    raise OSError(ctypes.get_errno(),'导入目标已存在或无法移动，未覆盖')
            finally:shutil.rmtree(stage,ignore_errors=True)
            result['imported'].append(ident)
        except Exception as error:result['errors'].append({'id':folder.name,'message':str(error)})
    return result

def trash_wallpaper(root,ident):
    if not ident or ident in ('.','..') or '/' in ident or '\\' in ident or ident.startswith('.'):raise ValueError('无效的壁纸编号')
    path=root/ident
    if path.is_symlink() or not path.is_dir() or path.resolve().parent!=root:raise ValueError('目标不是壁纸库中的直接目录')
    if not (path/'project.json').is_file():raise ValueError('目标不是壁纸目录')
    import gi
    from gi.repository import Gio
    Gio.File.new_for_path(str(path)).trash(None)
    return {'deleted':ident,'method':'trash'}

if __name__=='__main__':
    try:
        operation,library,value=sys.argv[1:]
        root=pathlib.Path(library)
        if not root.is_absolute() or not root.is_dir():raise ValueError('壁纸库目录不存在')
        root=root.resolve()
        lock=(root.parent/'.write.lock').open('a')
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('其他资源任务正在运行，请稍后重试')
        index=root.parent/'library.json'
        if index.exists() and json.loads(index.read_text()).get('version')!=1:raise ValueError('图库版本不兼容，停止写入')
        result=import_wallpapers(root,value) if operation=='import' else trash_wallpaper(root,value) if operation=='delete' else None
        if result is None:raise ValueError('未知操作')
        if index.exists():
            tmp=index.with_suffix('.json.tmp');tmp.write_text(json.dumps({'version':1,'entries':sorted(p.name for p in root.iterdir() if p.is_dir() and (p/'project.json').is_file())}));os.replace(tmp,index)
        print(json.dumps(result,ensure_ascii=False))
    except Exception as error:print(json.dumps({'error':str(error)},ensure_ascii=False));sys.exit(1)
