#!/usr/bin/env python3
"""Run package graphical acceptance in a prepared Debian rootfs, without host libraries.

The rootfs must contain a fresh project checkout at /work/project and locked build
and GNOME test dependencies. Only GPU devices and user-provided test resources
cross the boundary. No real session bus or user settings are exposed.
"""
import argparse, os, pathlib, subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('rootfs',type=pathlib.Path)
p.add_argument('archive',help='Absolute archive path inside the clean root')
p.add_argument('--runtime',type=pathlib.Path,required=True)
p.add_argument('--extensions',type=pathlib.Path,default=pathlib.Path.home()/'.local/share/gnome-shell/extensions')
p.add_argument('--video',action='store_true')
a=p.parse_args();fs=a.rootfs.resolve();runtime=a.runtime.resolve()
if not (fs/'work/project/packaging/check-desktop.py').is_file():p.error('Missing clean project checkout')
if not (fs/a.archive.lstrip('/')).is_file():p.error('Archive not found inside rootfs')
# GNOME needs a passwd entry; this modifies only the disposable rootfs.
passwd=fs/'etc/passwd';uid=os.getuid();gid=os.getgid()
if not any(line.split(':')[2]==str(uid) for line in passwd.read_text().splitlines()):
 with passwd.open('a') as out:out.write(f'wallpapertest:x:{uid}:{gid}:Isolated test:/root:/bin/bash\n')
(fs/'root/.local/share/gnome-shell/extensions').mkdir(parents=True,exist_ok=True)
(fs/'work/wallpaper-runtime').mkdir(parents=True,exist_ok=True)
command=['bwrap','--bind',str(fs),'/', '--dev-bind','/dev','/dev','--proc','/proc','--ro-bind','/sys','/sys',
 '--ro-bind',str(runtime),'/work/wallpaper-runtime',
 '--ro-bind',str(a.extensions.resolve()),'/root/.local/share/gnome-shell/extensions',
 '--clearenv','--setenv','HOME','/root','--setenv','PATH','/usr/sbin:/usr/bin:/sbin:/bin',
 '--setenv','LANG','C.UTF-8','--chdir','/work/project',
 'dbus-run-session','--','/bin/bash','-ec',
 'export DBUS_SYSTEM_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS"; exec "$@"',
 'clean-gnome-test','/usr/bin/python3','packaging/check-desktop.py',a.archive]
if a.video:command.append('--video')
before=subprocess.check_output(['dconf','dump','/org/gnome/'])
try:subprocess.run(command,check=True)
finally:
 if before!=subprocess.check_output(['dconf','dump','/org/gnome/']):raise RuntimeError('Actual desktop settings changed')
