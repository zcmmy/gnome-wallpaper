// Exercise real extension lifecycle methods with an asynchronous process stub.
const callbacks = new Map(); let serial = 0;
const GLib = {PRIORITY_DEFAULT: 0, SOURCE_REMOVE: false,
    get_monotonic_time: () => 10000000,
    timeout_add: (_p, ms, fn) => {callbacks.set(++serial, {ms, fn}); return serial;},
    source_remove: id => callbacks.delete(id)};
class Extension {}
const Gio = imports.gi.Gio;
const [, bytes] = Gio.File.new_for_path(ARGV[0]).load_contents(null);
let source = new TextDecoder().decode(bytes).replace(/^import .*;\r?\n/gm, '')
    .replace('export default class WallpaperEngineExtension', 'class WallpaperEngineExtension');
eval(source + '\nglobalThis.TestExtension = WallpaperEngineExtension;');
function assert(value, message) {if (!value) throw new Error(message);}
function setup() {
    callbacks.clear();
    const e = new globalThis.TestExtension(); const signals = [];
    const proc = {send_signal: s => signals.push(s), force_exit: () => signals.push('kill')};
    let enabled = true, starts = 0;
    Object.assign(e, {_proc:proc, _destroyed:false, _restartPending:false,
        _restartTimeoutId:0, _retryTimeoutId:0, _killTimeoutId:0, _matchTimeouts:new Set(),
        _paused:false, _procStopping:false, _procStartTime:0, _crashRetries:0,
        _settings:{get_boolean:()=>enabled}, _releaseWindow:()=>{}, _forgetWindow:()=>{},
        _stopPointerBridge:()=>{}, _startEngine:()=>{assert(e._proc === null,'started before exit'); starts++;}});
    return {e, proc, signals, enabled:v=>enabled=v, starts:()=>starts};
}
function restart(e) {e._scheduleRestart(); const [id,c] = [...callbacks].find(([,v])=>v.ms===700); callbacks.delete(id); c.fn();}
let t=setup(); restart(t.e); assert(t.starts()===0,'must await exit'); t.e._onEngineExited(t.proc);
assert(t.starts()===1,'must restart after exit'); assert(!t.e._killTimeoutId,'stale kill timer');
t=setup(); restart(t.e); t.enabled(false); t.e._onEngineExited(t.proc); assert(t.starts()===0,'disabled while stopping');
t=setup(); restart(t.e); restart(t.e); t.e._onEngineExited(t.proc); assert(t.starts()===1,'coalesce restart requests');
t=setup(); restart(t.e); t.e._destroyed=true; t.e._stopEngine(true); t.e._onEngineExited(t.proc);
assert(t.starts()===0 && t.signals.includes('kill'),'disable must reap a stopping child');
print('PASS: asynchronous restart, disable race, debounce, forced cleanup');
