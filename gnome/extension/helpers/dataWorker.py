#!/usr/bin/env python3
"""Transactional, cancellable user resource operations. No renderer or network."""
import argparse, fcntl, hashlib, json, os, pathlib, shutil, signal, stat, sys, tempfile

class Cancelled(Exception): pass

def emit(**value): print(json.dumps(value,ensure_ascii=False),flush=True)
def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def atomic_json(path,value):
    tmp=path.with_name('.'+path.name+'.tmp')
    with tmp.open('w') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
    os.replace(tmp,path);sync_directory(path.parent)
def inventory(folder):
    folder=pathlib.Path(folder).absolute()
    if folder.is_symlink() or not folder.is_dir():raise ValueError('请选择普通目录，不支持符号链接')
    files=[]
    def unreadable(error):raise error
    for base,dirs,names in os.walk(folder,followlinks=False,onerror=unreadable):
        for name in dirs+names:
            p=pathlib.Path(base)/name;mode=p.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):raise ValueError('目录包含链接或特殊文件，未导入')
        for name in names:
            p=pathlib.Path(base)/name;files.append((p.relative_to(folder),p.stat().st_size))
    return folder,files

def validate_assets(folder):
    folder,files=inventory(folder)
    for name in ['models','shaders','scripts']:
        if not (folder/name).is_dir() or not any(p.parts[0]==name and size>0 for p,size in files):
            raise ValueError('公共资源不完整：缺少有效的 '+name)
    return files

def validate_wallpaper(folder):
    folder,files=inventory(folder);p=folder/'project.json'
    if not p.is_file() or p.stat().st_size>1048576:raise ValueError('缺少有效 project.json')
    data=json.loads(p.read_text());kind=str(data.get('type','')).lower();entry=pathlib.Path(str(data.get('file','')))
    if kind not in ['scene','video']:raise ValueError('仅支持场景和视频壁纸')
    if entry.is_absolute() or '..' in entry.parts or not entry.parts:raise ValueError('无效入口路径')
    if not (folder/entry).is_file() and not (kind=='scene' and (folder/'scene.pkg').is_file()):raise ValueError('缺少入口文件或 scene.pkg')
    return files

def candidates(source):
    source=pathlib.Path(source).absolute()
    inventory(source) # Reject links in the entire user-selected subtree.
    result=[source] if (source/'project.json').is_file() else sorted(p for p in source.iterdir() if p.is_dir() and (p/'project.json').is_file())
    if not result:raise ValueError('没有找到可导入的壁纸')
    return result

def copy_checked(source,target,files,progress):
    target.mkdir(parents=True)
    for rel,size in files:
        if rel.name=='thumbnail.jpg' or any(p.startswith('.capture') for p in rel.parts):continue
        src=source/rel;dst=target/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        directory=os.open(source,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            for part in rel.parts[:-1]:
                child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory);os.close(directory);directory=child
            fd=os.open(rel.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
        finally:os.close(directory)
        with os.fdopen(fd,'rb') as inp,dst.open('xb') as out:
            before=os.fstat(inp.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size!=size:raise ValueError('来源文件已改变，请重新导入')
            digest=hashlib.sha256()
            while True:
                buf=inp.read(1024*1024)
                if not buf:break
                out.write(buf);digest.update(buf);progress['done']+=len(buf)
                emit(progress=progress['done'],total=progress['total'])
            after=os.fstat(inp.fileno());out.flush();os.fsync(out.fileno())
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('来源文件在复制时改变')
        check=hashlib.sha256()
        with dst.open('rb') as verify:
            for buf in iter(lambda:verify.read(1024*1024),b''):check.update(buf)
        if check.digest()!=digest.digest():raise ValueError('复制校验失败')
        sync_directory(dst.parent)
    for base,_,_ in os.walk(target,topdown=False):sync_directory(base)

def update_index(root):
    entries=[]
    for p in sorted((root/'wallpapers').iterdir()):
        if p.is_dir() and not p.is_symlink() and (p/'project.json').is_file():entries.append(p.name)
    atomic_json(root/'library.json',{'version':1,'entries':entries})

def recover(root):
    # Journal is written before publication. Finish only owned, validated moves.
    for stage in root.glob('.transaction-*'):
        if stage.is_symlink() or not stage.is_dir():continue
        journal=stage/'journal.json'
        if not journal.exists():shutil.rmtree(stage);continue
        data=json.loads(journal.read_text())
        for move in data['moves']:
            src=stage/move['source'];dst=root/move['target']
            if pathlib.Path(move['source']).name!=move['source']:raise ValueError('Invalid transaction source')
            rel=pathlib.Path(move['target'])
            if rel.is_absolute() or '..' in rel.parts or not (str(rel)=='assets' or len(rel.parts)==2 and rel.parts[0]=='wallpapers'):raise ValueError('Invalid transaction destination')
            if not src.exists():continue
            if dst.exists():
                if str(rel)!='assets':raise ValueError('恢复事务时发现同名壁纸，未覆盖')
                # Persist a marker so a crash after exchange cannot exchange back.
                if (stage/'assets-published').exists():continue
                # Rename old assets aside then publish. Recovery resumes this bounded gap.
                old=stage/'previous-assets'
                if not old.exists():
                    os.rename(dst,old);sync_directory(root);sync_directory(stage)
            os.rename(src,dst);sync_directory(dst.parent);sync_directory(stage)
            if str(rel)=='assets':(stage/'assets-published').touch()
        update_index(root)
        shutil.rmtree(stage)

def run(root,request):
    root=pathlib.Path(root).absolute();root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if root.is_symlink():raise ValueError('数据目录不能是符号链接')
    for name in ['wallpapers','assets','.write.lock','library.json']:
        if (root/name).is_symlink():raise ValueError('管理目录中存在符号链接，停止写入')
    (root/'wallpapers').mkdir(exist_ok=True)
    with (root/'.write.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('其他导入、迁移或截图任务正在使用资源，请稍后重试')
        index=root/'library.json'
        if index.exists() and json.loads(index.read_text()).get('version')!=1:raise ValueError('图库格式不兼容，停止写入')
        recover(root)
        op=request['operation']
        if op=='status':
            used=sum(size for _,size in inventory(root/'wallpapers')[1])
            try:validate_assets(root/'assets');assets=True
            except (ValueError,OSError):assets=False
            return {'assets':assets,'bytes':used,'entries':len(list((root/'wallpapers').iterdir()))}
        sources=[];skipped=[];moves=[]
        if op in ['assets','migrate']:
            src=pathlib.Path(request['assets']).absolute()
            if src.resolve()==root or root.is_relative_to(src.resolve()):raise ValueError('不能导入数据目录自身或上级目录')
            if (root/'assets').exists() and not request.get('replace'):
                if op=='assets':raise ValueError('已有公共资源，替换需要确认')
                skipped.append('assets')
            else:sources.append((src,'assets',validate_assets(src)))
        if op in ['import','migrate']:
            for folder in candidates(request['source']):
                ident=folder.name
                if ident.startswith('.') or folder.resolve()==root or root.is_relative_to(folder.resolve()):raise ValueError('不能导入数据目录自身或上级目录')
                if (root/'wallpapers'/ident).exists():skipped.append(ident);continue
                sources.append((folder,'wallpapers/'+ident,validate_wallpaper(folder)))
        if op not in ['assets','import','migrate']:raise ValueError('未知资源操作')
        total=sum(size for _,_,files in sources for _,size in files)
        if shutil.disk_usage(root).free<total+16*1024*1024:raise ValueError('数据盘空间不足')
        if request.get('plan'):return {'bytes':total,'files':sum(len(f) for _,_,f in sources),'skipped':skipped,'items':[i for _,i,_ in sources]}
        stage=pathlib.Path(tempfile.mkdtemp(prefix='.transaction-',dir=root));committing=False
        try:
            progress={'done':0,'total':total}
            for number,(src,ident,files) in enumerate(sources):
                name='item-'+str(number);copy_checked(src,stage/name,files,progress)
                (validate_assets if ident=='assets' else validate_wallpaper)(stage/name)
                moves.append({'source':name,'target':ident})
            atomic_json(stage/'journal.json',{'version':1,'moves':moves});committing=True
            # Cancellation is safe before commit; finish a short journalled commit once begun.
            signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
            recover(root)
            return {'imported':[pathlib.Path(i).name for _,i,_ in sources if i!='assets'],'skipped':skipped,'errors':[],'bytes':total}
        finally:
            if not committing:shutil.rmtree(stage,ignore_errors=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);args=p.parse_args()
    def cancel(*_):raise Cancelled('操作已取消，原文件保留')
    signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
    try:emit(result=run(args.root,json.load(sys.stdin)))
    except Exception as e:emit(error=str(e));raise SystemExit(1)
if __name__=='__main__':main()
