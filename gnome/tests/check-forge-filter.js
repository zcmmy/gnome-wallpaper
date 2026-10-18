// Exercise the actual ownership filter without running a compositor.
const Gio = imports.gi.Gio;
const callbacks=[];
const holdCompositing=()=>{};
const GLib={PRIORITY_DEFAULT:0, timeout_add:(_p,_ms,fn)=>{callbacks.push(fn);return callbacks.length;}};
class Extension {}
let manager;
const Main={extensionManager:{lookup:()=>({stateObj:{extWm:manager}})}};
const [,bytes]=Gio.File.new_for_path(ARGV[0]).load_contents(null);
const source=new TextDecoder().decode(bytes).replace(/^import .*;\r?\n/gm,'')
    .replace('export default class WallpaperEngineExtension','class WallpaperEngineExtension');
eval(source+'\nglobalThis.TestExtension=WallpaperEngineExtension;');
function assert(value,message){if(!value)throw new Error(message);}
const e=new globalThis.TestExtension();
const owned={get_pid:()=>42},ordinary={get_pid:()=>42}; // Same PID/title must not claim other apps.
const events=[];
Object.assign(e,{_waylandClient:{owns_window:w=>w===owned,
    make_desktop:w=>events.push(['desktop',w]),hide_from_window_list:w=>events.push(['hide',w])},
    _rendererWindow:null,_proc:{},_destroyed:false,_matchTimeouts:new Set()});
const original=function(w){assert(this===manager,'receiver changed');return w!==null;};
manager=Object.create({_validWindow:original});
e._protectFromTiling();const wrapper=manager._validWindow;
e._protectFromTiling();assert(wrapper===manager._validWindow,'duplicate wrapping');
assert(!manager._validWindow(owned),'renderer entered Forge');
assert(manager._validWindow(ordinary),'ordinary application excluded');
e._onWindowCreated(ordinary);assert(!events.length && !callbacks.length,'touched unrelated window');
e._onWindowCreated(owned);assert(events[0][0]==='desktop' && callbacks.length===1,'desktop role was delayed');
e._restoreTilingFilter();assert(manager._validWindow===original && !Object.hasOwn(manager,'_validWindow'),'inherited method not restored');
e._protectFromTiling();const currentWrapper=manager._validWindow;const other=function(w){return currentWrapper.call(this,w);};manager._validWindow=other;
e._restoreTilingFilter();assert(manager._validWindow===other,'overwrote another extension');
assert(currentWrapper.call(manager,owned),'detached wrapper remains active');
manager=null;e._protectFromTiling();
manager={_validWindow:original};e._protectFromTiling();assert(!manager._validWindow(owned),'new Forge instance unprotected');
e._restoreTilingFilter();assert(manager._validWindow===original,'own method not restored');
print('PASS: Forge ownership, synchronous desktop role, repeated starts, replacement instance, cleanup');
