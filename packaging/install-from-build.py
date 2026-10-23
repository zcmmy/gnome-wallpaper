#!/usr/bin/env python3
"""Package an existing build, then use the atomic full-package installer.

No rebuilding, source symlinks, resource migration or extension enablement.
The ordinary installer confirmation follows successful package preparation.
"""
import argparse,pathlib,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir',type=pathlib.Path,default=ROOT/'build/package-renderer')
    parser.add_argument('--destination',type=pathlib.Path)
    parser.add_argument('--isolated',action='store_true')
    parser.add_argument('--yes',action='store_true')
    args=parser.parse_args()
    if args.isolated and not args.destination:parser.error('--isolated requires --destination')
    if not (args.build_dir/'backend-build.json').is_file():
        parser.error('No recorded backend build. Run make package-backend first, or select --build-dir.')
    with tempfile.TemporaryDirectory(prefix='wallpaper-install-build-') as tmp:
        package=pathlib.Path(tmp)/'package'
        subprocess.run([sys.executable,str(ROOT/'packaging/build-package.py'),'--build-dir',str(args.build_dir.resolve()),'--output',str(package)],check=True)
        archive=package/('gnome-wallpaper-'+(ROOT/'VERSION').read_text().strip()+'-linux-x86_64.shell-extension.zip')
        command=[sys.executable,str(ROOT/'packaging/install.py'),str(archive)]
        if args.destination:command+=['--destination',str(args.destination.absolute())]
        if args.isolated:command+=['--isolated']
        if args.yes:command+=['--yes']
        subprocess.run(command,check=True)
if __name__=='__main__':main()
