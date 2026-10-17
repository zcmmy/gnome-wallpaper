import hashlib,json,pathlib,subprocess
r=pathlib.Path(__file__).resolve().parents[2];out=r/'reports/hq-capture/library';out.mkdir(parents=True,exist_ok=True)
result=[]
for project in sorted((r/'wallpapers').glob('*/project.json')):
 scene=project.parent;ident=scene.name;dest=out/(ident+'.png')
 before=hashlib.sha256((scene/'static-background.png').read_bytes()).hexdigest()
 cmd=['python3',str(r/'gnome/extension/captureWorker.py'),'--renderer',str(r/'renderer/scripts/run.sh'),'--assets',str(r/'assets'),'--scene',str(scene),'--output',str(dest),'--diagnostics',str(out/ident)]
 run=subprocess.run(cmd,text=True,capture_output=True,timeout=150)
 if run.returncode:raise RuntimeError(ident+': '+run.stdout+run.stderr)
 data=json.loads(run.stdout);meta=json.loads((out/ident/'capture.png.reference.json').read_text());c=meta['captures'][0]
 visible=[c['width']*abs(c['uv'][1]-c['uv'][0]),c['height']*abs(c['uv'][3]-c['uv'][2])]
 if data['type'].lower()=='scene':assert visible[0]>=3839 and visible[1]>=2159,(ident,visible)
 data.update(id=ident,old_source_sha256=before,framebuffer=[c['width'],c['height']],visible_pixels=visible)
 result.append(data);(out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(ident,data['type'],data['framebuffer'],'-> 1920x1080',data['elapsed'],'seconds',flush=True)
