// Exercise the actual focus policy without a live desktop.
const Gio = imports.gi.Gio;
const Meta = {TabList: {NORMAL: 0}};
const [, bytes] = Gio.File.new_for_path(ARGV[0]).load_contents(null);
eval(new TextDecoder().decode(bytes).replace(/^import .*;\r?\n/gm, '')
    .replace('export function', 'function') + '\nglobalThis.restoreFocus = restoreWorkspaceFocus;');
function assert(value, message) {if (!value) throw new Error(message);}
const workspace = {}, otherWorkspace = {}, renderer = {}, calls = [];
let windows = [], lookups = 0;
const global = {
    display: {focus_window: renderer,
        get_tab_list: (type, ws) => {assert(type === 0 && ws === workspace, 'cross-workspace query'); lookups++; return windows;},
        unset_input_focus: time => calls.push(['unset', time])},
    workspace_manager: {get_active_workspace: () => workspace},
    get_current_time: () => 0,
};
function window(ws = workspace, flags = {}) {
    return {located_on_workspace: w => w === ws, showing_on_its_workspace: () => true,
        focus: time => calls.push(['focus', time]), activate: () => {throw new Error('activate called');}, ...flags};
}
const local = window(), remote = window(otherWorkspace);
windows = [renderer, remote, window(workspace, {minimized: true}), window(workspace, {skip_taskbar: true}),
    window(workspace, {showing_on_its_workspace: () => false}), local];
globalThis.restoreFocus(renderer);assert(JSON.stringify(calls) === '[["focus",0]]', 'visible current app not focused');
windows = [remote, window(workspace, {minimized: true})];calls.length = 0;
globalThis.restoreFocus(renderer);assert(JSON.stringify(calls) === '[["unset",0]]', 'empty workspace retained focus');
calls.length = 0;global.display.focus_window = local;const before = lookups;
globalThis.restoreFocus(renderer);globalThis.restoreFocus(null);
assert(!calls.length && lookups === before, 'mapping stole focus from existing app');
print('PASS: workspace-local focus, empty desktop, minimized/hidden exclusions, zero timestamp, no activation');
