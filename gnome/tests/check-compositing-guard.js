// Read the real module with controlled compositor APIs; never touch the desktop.
const Gio = imports.gi.Gio;
const Meta = {};
const global = {display:{}};
const [,bytes] = Gio.File.new_for_path(ARGV[0]).load_contents(null);
const source = new TextDecoder().decode(bytes).replace(/^import .*;\r?\n/gm, '').replace(/export function /g, 'function ');
eval(source + '\nglobalThis.hold=holdCompositing;globalThis.release=releaseCompositing;');
function assert(value, message) {if (!value) throw new Error(message);}
let count=1, acquired=0, released=0; // Another extension already holds one reference.
global.compositor={disable_unredirect(){count++;acquired++;},enable_unredirect(){count--;released++;}};
const ext={};
release(ext);assert(count===1,'static mode released a foreign reference');
hold(ext);hold(ext);assert(count===2&&acquired===1,'duplicate acquire');
const otherCompositor=global.compositor;
global.compositor={enable_unredirect(){throw new Error('released wrong compositor');}};
release(ext);release(ext);assert(count===1&&released===1&&!ext._compositingRelease,'unbalanced release');
global.compositor=otherCompositor;
for(let i=0;i<3;i++){hold(ext);release(ext);}assert(count===1,'restart leaks');
global.compositor=null;
Meta.disable_unredirect_for_display=display=>{assert(display===global.display,'wrong display');count++;};
Meta.enable_unredirect_for_display=display=>{assert(display===global.display,'wrong display');count--;};
hold(ext);hold(ext);release(ext);assert(count===1,'legacy balance');
Meta.disable_unredirect_for_display=()=>{throw new Error('acquisition failed');};
let failed=false;try{hold(ext);}catch(_){failed=true;}
assert(failed&&!ext._compositingRelease&&count===1,'failed acquire owns a reference');
delete Meta.disable_unredirect_for_display;delete Meta.enable_unredirect_for_display;
failed=false;try{hold(ext);}catch(_){failed=true;}assert(failed,'unsupported compositor silently accepted');
print('PASS: static no-op, balanced/idempotent acquire/release, restart, other owners, legacy API and failures');
