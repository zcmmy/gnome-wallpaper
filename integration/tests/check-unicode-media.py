#!/usr/bin/env python3
"""Synthetic multilingual MPRIS -> scene script -> pixels, on a private desktop."""
import argparse, json, os, pathlib, signal, subprocess, sys, time, shutil
import gi
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gio, GLib, GdkPixbuf

PAYLOAD = {'title':'中文音乐・日本語の歌・한국어노래',
           'artist':'藝術家・アーティスト・음악가', 'albumTitle':'专辑・アルバム・앨범'}

def mock_player(ready):
    node=Gio.DBusNodeInfo.new_for_xml('''<node><interface name="org.mpris.MediaPlayer2.Player">
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Position" type="x" access="read"/></interface></node>''')
    conn=Gio.bus_get_sync(Gio.BusType.SESSION,None)
    count=[0]
    def metadata():
        return GLib.Variant('a{sv}',{'xesam:title':GLib.Variant('s',PAYLOAD['title']),
          'xesam:artist':GLib.Variant('as',[PAYLOAD['artist']]),
          'xesam:album':GLib.Variant('s',PAYLOAD['albumTitle']),
          'mpris:length':GLib.Variant('x',60000000+count[0])})
    def get_property(connection,sender,path,iface,name):
        return {'PlaybackStatus':GLib.Variant('s','Playing'),'Position':GLib.Variant('x',1000000),'Metadata':metadata()}[name]
    conn.register_object('/org/mpris/MediaPlayer2',node.interfaces[0],None,get_property,None)
    owner=Gio.bus_own_name_on_connection(conn,'org.mpris.MediaPlayer2.UnicodeFixture',Gio.BusNameOwnerFlags.NONE,None,None)
    def emit():
        count[0]+=1
        conn.emit_signal(None,'/org/mpris/MediaPlayer2','org.freedesktop.DBus.Properties','PropertiesChanged',
                         GLib.Variant('(sa{sv}as)',('org.mpris.MediaPlayer2.Player',{'Metadata':metadata()},[])))
        return True
    GLib.timeout_add(400,emit)
    pathlib.Path(ready).touch()
    GLib.MainLoop().run()


def stop(proc):
    if proc and proc.poll() is None:
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.wait(timeout=4)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()

def image(path):
    p=GdkPixbuf.Pixbuf.new_from_file(str(path))
    assert (p.get_width(),p.get_height())==(1280,720)
    return bytes(p.get_pixels())

def run(args):
    root=pathlib.Path(__file__).resolve().parents[2]
    out=pathlib.Path(args.output).absolute();out.mkdir(parents=True,exist_ok=False)
    profile=out/'session'
    env=os.environ.copy()
    for key in ['DISPLAY','WAYLAND_DISPLAY','WAYLAND_SOCKET','DBUS_SESSION_BUS_ADDRESS']:env.pop(key,None)
    for key,sub in [('XDG_RUNTIME_DIR','run'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state')]:
        p=profile/sub;p.mkdir(parents=True);p.chmod(0o700);env[key]=str(p)
    env['UNICODE_TEST_PROFILE']=str(profile)
    script='''printf '%s' "$DBUS_SESSION_BUS_ADDRESS" > "$UNICODE_TEST_PROFILE/bus"
    gsettings set org.gnome.shell enabled-extensions '[]'
    gsettings set org.gnome.shell disable-user-extensions true
    gsettings set org.gnome.shell welcome-dialog-last-shown-version '48.0'
    exec gnome-shell --headless --virtual-monitor=1280x720 --wayland --wayland-display unicode-test --no-x11 --sm-disable'''
    shell=player=renderer=None
    try:
        with (out/'shell.log').open('w') as log:
            shell=subprocess.Popen(['dbus-run-session','--','bash','-ec',script],env=env,stdout=log,stderr=log,start_new_session=True)
        for _ in range(150):
            if (profile/'run/unicode-test').exists() and (profile/'bus').exists():break
            assert shell.poll() is None,'Private compositor exited'
            time.sleep(.1)
        else:raise RuntimeError('Private compositor timeout')
        env.update(WAYLAND_DISPLAY='unicode-test',DBUS_SESSION_BUS_ADDRESS=(profile/'bus').read_text(),LWE_LIGHTDUMP='1',vblank_mode='0')
        with (out/'player.log').open('w') as log:
            player=subprocess.Popen([sys.executable,__file__,'--mock-player',str(profile/'player-ready')],env=env,stdout=log,stderr=log,start_new_session=True)
        for _ in range(100):
            if (profile/'player-ready').exists():break
            assert player.poll() is None,'Mock MPRIS exited'
            time.sleep(.1)
        else:raise RuntimeError('MPRIS startup timeout')
        def capture(label,executable,dynamic):
            scene=out/label;scene.mkdir()
            (scene/'project.json').write_text(json.dumps({'title':'Unicode rendering fixture','type':'scene','file':'scene.json'}))
            rows=[('title',PAYLOAD['title']),('artist',PAYLOAD['artist']),('albumTitle',PAYLOAD['albumTitle']),
                  ('latin','LatinABC0123'),('other','Été・Ελληνικά・Русский・😀'),('limited',PAYLOAD['title']*3)]
            objects=[]
            shutil.copyfile('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',scene/'embedded.ttf')
            for i,(key,text) in enumerate(rows):
                value=text
                if dynamic and key in PAYLOAD:
                    value={'value':'WAIT','script':f"let current='WAIT'; export function mediaPropertiesChanged(e) {{ current=e.{key}; }} export function update() {{ return current; }}"}
                objects.append({'id':i+1,'name':key,'text':value,'origin':f'640 {100+i*95} 0','pointsize':36,'color':'1 1 1','font':'embedded.ttf' if key in ('artist','other') else 'systemfont_default',
                                'limitwidth':key=='limited','maxwidth':600,'limituseellipsis':True})
            (scene/'scene.json').write_text(json.dumps({'camera':{'center':'0 0 0','eye':'0 0 1','up':'0 1 0'},
                'general':{'orthogonalprojection':{'width':1280,'height':720},'clearcolor':'0.035 0.045 0.065'},'objects':objects},ensure_ascii=False))
            png=out/(label+'.png');logpath=out/(label+'.log')
            command=[executable,'--window','0x0x1280x720','--fps','15','--silent','--no-audioreactive','--no-fullscreen-pause',
                     '--screenshot',str(png),'--screenshot-delay','40','--assets-dir',str(pathlib.Path(args.assets).absolute()),str(scene)]
            # Direct binary only: its adjacent libraries plus the supplied runtime library directory.
            runenv=env.copy();runenv['LD_LIBRARY_PATH']=str(pathlib.Path(executable).resolve().parent)+':'+args.libraries
            with logpath.open('w') as log:
                proc=subprocess.Popen(command,env=runenv,stdout=log,stderr=log,start_new_session=True)
                try:
                    last=0
                    for _ in range(250):
                        if png.exists():
                            n=png.stat().st_size
                            if n>100 and n==last:break
                            last=n
                        assert proc.poll() is None,'Renderer exited: '+label+' (see '+str(logpath)+')'
                        time.sleep(.1)
                    else:raise RuntimeError('Screenshot timeout: '+label)
                    return image(png)
                finally:stop(proc)
        fixed=capture('fixed-media',args.renderer,True)
        reference=capture('fixed-reference',args.renderer,False)
        assert fixed==reference,'MPRIS/script pixels differ from literal Unicode text'
        if args.baseline:
            old=capture('before-media',args.baseline,True)
            assert old!=fixed,'Baseline unexpectedly identical; fixture failed to reproduce'
            stride=len(old)//720
            # Fourth row: ASCII preserves the old font and pixels.
            assert old[300*stride:370*stride]==fixed[300*stride:370*stride], 'ASCII changed'
            assert len(set(fixed[300*stride:370*stride]))>5, 'ASCII reference is blank'
        (out/'result.json').write_text(json.dumps({'passed':True,'mpris_matches_literal_pixels':True,'baseline_compared':bool(args.baseline),'live_desktop_modified':False},indent=2)+'\n')
        print('PASS: isolated MPRIS -> QuickJS -> CText matches literal Unicode pixels' + ('; old/new difference and ASCII preservation' if args.baseline else ''))
    finally:stop(renderer);stop(player);stop(shell)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--mock-player':mock_player(sys.argv[2])
    else:
        p=argparse.ArgumentParser(description=__doc__)
        p.add_argument('--renderer',required=True);p.add_argument('--baseline');p.add_argument('--assets',required=True)
        p.add_argument('--libraries',default='');p.add_argument('--output',required=True)
        run(p.parse_args())
