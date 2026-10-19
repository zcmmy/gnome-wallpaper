import Meta from 'gi://Meta';

// A desktop surface can receive focus during workspace transitions or clicks.
// Returning it is not an application launch: activate() may switch workspaces,
// unminimize/raise an app, or generate demands-attention when its timestamp is 0.
export function restoreWorkspaceFocus(rendererWindow) {
    if (!rendererWindow || global.display.focus_window !== rendererWindow)
        return;

    const workspace = global.workspace_manager.get_active_workspace();
    const target = global.display.get_tab_list(Meta.TabList.NORMAL, workspace)
        .find(window => window !== rendererWindow && !window.skip_taskbar &&
            !window.minimized && window.located_on_workspace(workspace) &&
            window.showing_on_its_workspace());
    const timestamp = global.get_current_time();
    if (target)
        target.focus(timestamp);
    else
        global.display.unset_input_focus(timestamp);
}
