#!/usr/bin/env python3
"""Tie a completed backend build to exact renderer inputs and output hashes."""
import hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1];build=pathlib.Path(sys.argv[1]).resolve()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
if subprocess.check_output(['git','-C',str(root),'status','--porcelain','--','renderer/source'],text=True).strip():
 raise SystemExit('Commit renderer inputs before recording a distributable build')
record={'format':1,'renderer_tree':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD:renderer/source'],text=True).strip(),
        'outputs':{name:digest(build/'output'/name) for name in ['linux-wallpaperengine','liblinux-wallpaperengine-lib.so']}}
(build/'backend-build.json').write_text(json.dumps(record,indent=2)+'\n')
