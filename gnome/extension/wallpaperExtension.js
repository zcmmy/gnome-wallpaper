// Wallpaper Engine for Wayland - GNOME Shell extension
// Spawns linux-wallpaperengine or mpv as a background renderer process and
// embeds its window into GNOME Shell's background group so it sits strictly
// behind desktop icons and application windows.

import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Meta from 'gi://Meta';
import Clutter from 'gi://Clutter';
import {PointerBridge} from './pointerBridge.js';
import {OverviewWallpaper} from './overviewWallpaper.js';
import {StaticOverview} from './staticOverview.js';
import {WallpaperManager} from './manager.js';
import {scenePath} from './library.js';

import {Extension, InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {WorkspaceGroup} from 'resource:///org/gnome/shell/ui/workspaceAnimation.js';

const MPV_APP_ID = 'gwe-mpv-renderer';


// Bumped on every code change; logged from enable() so we can tell which
// revision the running shell actually loaded (see the comment there).
const CODE_REVISION = 13;

const SIGTERM = 15;
const SIGCONT = 18;
const SIGSTOP = 19;

const RESTART_DEBOUNCE_MS = 700;
const CRASH_RETRY_DELAY_MS = 2000;
const MAX_CRASH_RETRIES = 3;
const STABLE_RUNTIME_US = 30 * 1000 * 1000; // 30s uptime resets the retry counter
const WINDOW_MATCH_RETRIES = 450;
const WINDOW_MATCH_INTERVAL_MS = 100;

function expandTilde(path) {
    if (path.startsWith('~/'))
        return GLib.build_filenamev([GLib.get_home_dir(), path.slice(2)]);
    if (path === '~')
        return GLib.get_home_dir();
    return path;
}

export default class WallpaperEngineExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        // Dynamic intent persists across switches and screen lock, but never
        // launches on a new login without a fresh explicit UI action.
        if (!this._everEnabled) {this._settings.set_boolean('enabled', false); this._everEnabled = true;}
        this._destroyed = false;
        this._restartPending = false;
        this._pointerBridge = null;
        this._socketDir = GLib.dir_make_tmp('wallpaper-adapter-XXXXXX');
        this._socketPath = GLib.build_filenamev([this._socketDir, 'renderer.sock']);

        this._proc = null;
        this._waylandClient = null;
        this._procStopping = false;
        this._procStartTime = 0;
        this._paused = false;
        this._crashRetries = 0;

        // Deliberately at warning level so it always reaches the journal:
        // on Wayland the shell never re-imports extension code within a
        // session, so this is how we verify which revision is actually live.
        console.warn(`[wallpaperengine@waylandwe] enabled, code revision ${CODE_REVISION}`);

        this._rendererWindow = null;
        this._rendererActor = null;
        this._rendererLayer = null;
        this._rendererUnmanagedId = 0;
        this._rendererRaisedId = 0;
        this._rendererFocusId = 0;
        this._bgChildAddedId = 0;
        this._rendererVisibleId = 0;
        this._rendererFirstFrameId = 0;
        this._rendererReady = false;
        this._rendererGeometryIds = [];

        this._restartTimeoutId = 0;
        this._retryTimeoutId = 0;
        this._killTimeoutId = 0;
        this._matchTimeouts = new Set();

        this._injectionManager = new InjectionManager();
        this._overviewWallpaper = null;
        this._embeddingActive = false;

        this._windowCreatedId = global.display.connect(
            'window-created', (_display, window) => this._onWindowCreated(window));

        this._monitorsChangedId = Main.layoutManager.connect(
            'monitors-changed', () => this._scheduleRestart());

        this._settingsChangedId = this._settings.connect(
            'changed', (_settings, key) => this._manager?.changed(key));

        // Suspend rendering while the screensaver / screen blank is active.
        // (The full lock screen additionally disables this extension entirely
        // because metadata.json only declares the "user" session mode.)
        this._screenSaverSubId = Gio.DBus.session.signal_subscribe(
            'org.gnome.ScreenSaver',
            'org.gnome.ScreenSaver',
            'ActiveChanged',
            '/org/gnome/ScreenSaver',
            null,
            Gio.DBusSignalFlags.NONE,
            (_conn, _sender, _path, _iface, _signal, params) => {
                const [active] = params.deep_unpack();
                this._setPaused(active);
                this._manager?.suspend(active);
            });

        this._staticOverview = new StaticOverview(this);
        this._manager = new WallpaperManager(this);
        this._manager.start();
    }

    disable() {
        this._staticOverview?.destroy();
        this._staticOverview = null;
        this._manager?.destroy();
        this._manager = null;
        this._overviewWallpaper?.destroy();
        this._overviewWallpaper = null;
        this._destroyed = true;
        this._restoreTilingFilter();
        this._restartPending = false;
        this._stopPointerBridge();

        if (this._injectionManager) {
            this._injectionManager.clear();
            this._injectionManager = null;
        }

        if (this._windowCreatedId) {
            global.display.disconnect(this._windowCreatedId);
            this._windowCreatedId = 0;
        }
        if (this._monitorsChangedId) {
            Main.layoutManager.disconnect(this._monitorsChangedId);
            this._monitorsChangedId = 0;
        }
        if (this._settingsChangedId) {
            this._settings.disconnect(this._settingsChangedId);
            this._settingsChangedId = 0;
        }
        if (this._screenSaverSubId) {
            Gio.DBus.session.signal_unsubscribe(this._screenSaverSubId);
            this._screenSaverSubId = 0;
        }

        this._clearTimeouts();
        this._stopEngine(true);

        this._settings = null;
        GLib.unlink(this._socketPath);
        GLib.rmdir(this._socketDir);
    }

    // Mutter hides the owned client from Overview, Alt-Tab and app lists.
    // Only the workspace animation needs a local filter because its stacking
    // code assumes every normal window actor remains in the normal stack.
    _installOverviewHiding() {
        const extension = this;
        this._injectionManager.overrideMethod(WorkspaceGroup.prototype, '_shouldShowWindow',
            original => function (window) {
                return extension._windowMatchesRenderer(window) ? false : original.call(this, window);
            });
    }

    _clearTimeouts() {
        if (this._restartTimeoutId) {
            GLib.source_remove(this._restartTimeoutId);
            this._restartTimeoutId = 0;
        }
        if (this._retryTimeoutId) {
            GLib.source_remove(this._retryTimeoutId);
            this._retryTimeoutId = 0;
        }
        if (this._killTimeoutId) {
            GLib.source_remove(this._killTimeoutId);
            this._killTimeoutId = 0;
        }
        for (const id of this._matchTimeouts)
            GLib.source_remove(id);
        this._matchTimeouts.clear();
    }

    // ---------------------------------------------------------------- geometry

    _targetMonitorIndex() {
        const monitors = Main.layoutManager.monitors;
        let index = this._settings.get_int('monitor-index');
        if (index < 0 || index >= monitors.length)
            index = Main.layoutManager.primaryIndex;
        return index;
    }

    _targetGeometry() {
        const monitor = Main.layoutManager.monitors[this._targetMonitorIndex()];
        return {
            x: monitor.x,
            y: monitor.y,
            width: monitor.width,
            height: monitor.height,
        };
    }

    // ------------------------------------------------------------ command line

    _resolveEngine() {
        if (this._settings.get_string('library-root')) return 'wallpaperengine';
        const engine = this._settings.get_string('engine');
        if (engine !== 'auto')
            return engine;

        const sceneConfigured = this._settings.get_string('wallpaper-id').trim() !== '';
        const weBinary = expandTilde(this._settings.get_string('wallpaperengine-path'));
        const weFound = GLib.path_is_absolute(weBinary)
            ? GLib.file_test(weBinary, GLib.FileTest.IS_EXECUTABLE)
            : GLib.find_program_in_path(weBinary) !== null;

        if (sceneConfigured && weFound)
            return 'wallpaperengine';
        return 'mpv';
    }

    _resolveScenePath() {
        const library = expandTilde(this._settings.get_string('library-root'));
        if (library) return scenePath(library, this._settings.get_string('selected-id'));
        const raw = this._settings.get_string('wallpaper-id').trim();
        if (raw === '')
            return null;

        if (/^\d+$/.test(raw)) {
            const workshop = expandTilde(this._settings.get_string('workshop-path'));
            const candidate = GLib.build_filenamev([workshop, raw]);
            if (GLib.file_test(candidate, GLib.FileTest.EXISTS))
                return candidate;
            // Let linux-wallpaperengine try to locate the bare ID itself.
            return raw;
        }
        return expandTilde(raw);
    }

    _buildWallpaperEngineArgv() {
        const scene = this._resolveScenePath();
        if (scene === null) {
            this._notifyError(
                'No Wallpaper Engine scene configured. Set a Workshop item ID or scene path in the extension preferences.');
            return null;
        }

        const geo = this._targetGeometry();
        const fps = this._settings.get_int('fps');
        const scaling = this._settings.get_string('scaling');
        const argv = [
            expandTilde(this._settings.get_string('wallpaperengine-path')),
            '--fps', String(fps),
            '--listen', '--no-fullscreen-pause',
            '--scaling', scaling,
            // GNOME's Mutter does not implement wlr-layer-shell, so the
            // engine renders into a normal window sized to the monitor; the
            // extension then reparents that window behind the desktop.
            '--window', `0x0x${geo.width}x${geo.height}`,
        ];

        if (this._settings.get_boolean('mute'))
            argv.push('--silent');
        else
            argv.push('--volume', String(this._settings.get_int('volume')));

        const assets = expandTilde(this._settings.get_string('assets-path').trim());
        if (assets !== '')
            argv.push('--assets-dir', assets);

        argv.push(scene);
        return argv;
    }

    _buildMpvArgv() {
        const video = expandTilde(this._settings.get_string('video-path').trim());
        if (video === '') {
            this._notifyError(
                'No video file configured. Pick an MP4/WebM/GIF in the extension preferences.');
            return null;
        }
        if (!GLib.file_test(video, GLib.FileTest.EXISTS)) {
            this._notifyError(`Video file not found: ${video}`);
            return null;
        }

        const fps = this._settings.get_int('fps');
        const scaling = this._settings.get_string('scaling');
        const mute = this._settings.get_boolean('mute');
        const volume = this._settings.get_int('volume');

        const argv = [
            expandTilde(this._settings.get_string('mpv-path')),
            '--no-config',
            '--really-quiet',
            '--force-window=yes',
            '--no-border',
            '--no-osc',
            '--no-osd-bar',
            '--no-input-default-bindings',
            '--input-vo-keyboard=no',
            '--no-input-cursor',
            '--cursor-autohide=no',
            '--no-stop-screensaver',
            '--no-audio-display',
            '--hwdec=auto-safe',
            '--loop-file=inf',
            `--title=${MPV_APP_ID}`,
            `--wayland-app-id=${MPV_APP_ID}`,
            `--x11-name=${MPV_APP_ID}`,
            `--vf=fps=${fps}`,
            `--volume=${volume}`,
            mute ? '--mute=yes' : '--mute=no',
        ];

        if (scaling === 'fill')
            argv.push('--panscan=1.0');
        else if (scaling === 'stretch')
            argv.push('--keepaspect=no');

        argv.push(video);
        return argv;
    }

    // ------------------------------------------------------- process lifecycle

    _startEngine() {
        if (this._proc !== null || this._destroyed || !this._settings.get_boolean('enabled'))
            return;
        if (Main.layoutManager.monitors.length === 0)
            return;

        const engine = this._resolveEngine();
        const argv = engine === 'wallpaperengine'
            ? this._buildWallpaperEngineArgv()
            : this._buildMpvArgv();
        if (argv === null)
            return;

        if (!this._embeddingActive) {
            this._installOverviewHiding(); this._embeddingActive = true;
        }

        this._protectFromTiling();
        let proc;
        this._waylandClient = null;
        try {
            const launcher = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.NONE});
            launcher.setenv('LWE_SOCKET', this._socketPath, true);
            const logDir = GLib.build_filenamev([GLib.get_user_state_dir(), 'wallpaper-adapter']);
            GLib.mkdir_with_parents(logDir, 0o700);
            launcher.set_stdout_file_path(GLib.build_filenamev([logDir, 'renderer.log']));
            launcher.set_stderr_file_path(GLib.build_filenamev([logDir, 'renderer-error.log']));
            if (Meta.is_wayland_compositor()) {
                this._waylandClient = Meta.WaylandClient.new(global.context, launcher);
                proc = this._waylandClient.spawnv(global.display, argv);
            } else {
                throw new Error('This integration requires a GNOME Wayland session');
            }
        } catch (e) {
            this._waylandClient = null;
            this._notifyError(`Failed to launch "${argv[0]}": ${e.message}`);
            return;
        }

        this._proc = proc;
        this._restartPending = false;
        this._procStopping = false;
        this._paused = false;
        this._procStartTime = GLib.get_monotonic_time();
        this._manager?.launched();

        proc.wait_async(null, (p, res) => {
            try {
                p.wait_finish(res);
            } catch (_e) {
                // Cancelled or reaping failed; treat as exit.
            }
            this._onEngineExited(p);
        });
    }

    _onEngineExited(proc) {
        if (proc !== this._proc || this._destroyed)
            return;

        const wasStopping = this._procStopping;
        const uptime = GLib.get_monotonic_time() - this._procStartTime;
        this._proc = null;
        this._waylandClient = null;
        this._procStopping = false;
        this._paused = false;
        this._stopPointerBridge();
        this._forgetWindow();
        if (this._killTimeoutId) {
            GLib.source_remove(this._killTimeoutId);
            this._killTimeoutId = 0;
        }

        if (wasStopping) {
            this._manager?.publish();
            if (this._restartPending && this._settings?.get_boolean('enabled')) {
                this._restartPending = false;
                this._startEngine();
            }
            return;
        }

        this._stopEngine();
        this._manager?.failed('渲染器已退出。静态背景已保留；请检查资源或点击重试。');
    }

    _stopEngine(immediate = false) {
        this._manager?.cancelCapture();
        this._manager?.clearWatchdog();
        this._overviewWallpaper?.destroy(); this._overviewWallpaper = null;
        this._injectionManager?.clear(); this._embeddingActive = false;
        if (this._rendererActor) this._rendererActor.opacity = 0;
        this._stopPointerBridge();
        if (this._retryTimeoutId) {
            GLib.source_remove(this._retryTimeoutId);
            this._retryTimeoutId = 0;
        }
        for (const id of this._matchTimeouts)
            GLib.source_remove(id);
        this._matchTimeouts.clear();

        this._releaseWindow();
        this._staticOverview?.sync();

        const proc = this._proc;
        if (proc === null)
            return;
        if (this._procStopping) {
            if (immediate)
                proc.force_exit();
            return;
        }

        this._procStopping = true;

        if (this._paused) {
            try {
                proc.send_signal(SIGCONT);
            } catch (_e) {
                // Process already gone.
            }
            this._paused = false;
        }

        if (immediate) {
            proc.force_exit();
            return;
        }

        try {
            proc.send_signal(SIGTERM);
        } catch (_e) {
            return;
        }

        this._killTimeoutId = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT, 3000, () => {
                this._killTimeoutId = 0;
                if (this._proc === proc && this._procStopping)
                    proc.force_exit();
                return GLib.SOURCE_REMOVE;
            });
    }

    _scheduleRestart() {
        if (this._destroyed)
            return;
        if (this._restartTimeoutId) {
            GLib.source_remove(this._restartTimeoutId);
            this._restartTimeoutId = 0;
        }
        this._restartTimeoutId = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT, RESTART_DEBOUNCE_MS, () => {
                this._restartTimeoutId = 0;
                this._crashRetries = 0;
                this._restartPending = this._settings?.get_boolean('enabled') ?? false;
                this._stopEngine();
                if (this._proc === null && this._restartPending)
                    this._startEngine();
                return GLib.SOURCE_REMOVE;
            });
    }

    _setPaused(paused) {
        if (this._proc === null || this._procStopping || paused === this._paused)
            return;
        try {
            this._proc.send_signal(paused ? SIGSTOP : SIGCONT);
            this._paused = paused;
        } catch (_e) {
            // Process already gone; the exit handler will clean up.
        }
    }

    // -------------------------------------------------------- window embedding

    // Forge may receive window-created before us. Its bound signal handler
    // calls _validWindow dynamically, so filter only our owned client before
    // spawn. A floating-window rule is insufficient: Forge can keep floats above.
    _protectFromTiling() {
        const manager = Main.extensionManager.lookup('forge@jmmaranan.com')?.stateObj?.extWm;
        if (manager && this._tilingFilter?.manager === manager) return;
        this._restoreTilingFilter();
        if (typeof manager?._validWindow !== 'function') return;
        const extension = this;
        const filter = {manager, original: manager._validWindow,
            descriptor: Object.getOwnPropertyDescriptor(manager, '_validWindow'), active: true};
        filter.wrapper = function (window, ...args) {
            if (filter.active && extension._windowMatchesRenderer(window)) return false;
            return filter.original.call(this, window, ...args);
        };
        manager._validWindow = filter.wrapper;
        this._tilingFilter = filter;
    }

    _restoreTilingFilter() {
        const filter = this._tilingFilter;
        if (!filter) return;
        filter.active = false;
        if (filter.manager._validWindow === filter.wrapper) {
            if (filter.descriptor) Object.defineProperty(filter.manager, '_validWindow', filter.descriptor);
            else delete filter.manager._validWindow;
        }
        this._tilingFilter = null;
    }

    _onWindowCreated(window) {
        if (this._proc === null || this._rendererWindow !== null || this._destroyed)
            return;

        if (!this._windowMatchesRenderer(window)) return;

        // Classify synchronously, before map/adoption polling. This also keeps
        // tilers enabled later from discovering the wallpaper as an application.
        this._waylandClient.make_desktop(window);
        this._waylandClient.hide_from_window_list(window);

        // wm_class / app-id and title may not be set at creation time on
        // Wayland; poll briefly before giving up on this window.
        let attempts = 0;
        const sourceId = GLib.timeout_add(
            GLib.PRIORITY_DEFAULT, WINDOW_MATCH_INTERVAL_MS, () => {
                attempts++;
                const done = this._tryAdoptWindow(window);
                if (done || attempts >= WINDOW_MATCH_RETRIES) {
                    this._matchTimeouts.delete(sourceId);
                    return GLib.SOURCE_REMOVE;
                }
                return GLib.SOURCE_CONTINUE;
            });
        this._matchTimeouts.add(sourceId);
    }

    _windowMatchesRenderer(window) {
        if (window == null)
            return false;

        // Callers aren't consistent about what they hand us: Workspace's
        // _isOverviewWindow passes a MetaWindow, WorkspaceThumbnail's passes
        // a MetaWindowActor. Accept both.
        if (typeof window.get_meta_window === 'function')
            window = window.get_meta_window();
        if (window == null || typeof window.get_pid !== 'function')
            return false;

        // Already adopted: identity beats every heuristic.
        if (window === this._rendererWindow)
            return true;

        // Never claim another application's window based on its title or app id.
        return this._waylandClient !== null && this._waylandClient.owns_window(window);
    }

    _tryAdoptWindow(window) {
        if (this._rendererWindow !== null || this._destroyed || this._procStopping)
            return true;
        if (!this._windowMatchesRenderer(window))
            return false;

        const actor = window.get_compositor_private();
        if (!actor)
            return false;

        this._rendererWindow = window;
        this._rendererActor = actor;

        this._waylandClient.hide_from_window_list(window);
        window.stick();
        if (window.is_above()) window.unmake_above();
        window.lower();

        const geo = this._targetGeometry();
        window.move_resize_frame(false, geo.x, geo.y, geo.width, geo.height);

        // Move the window's actor from the normal window stack into the
        // background group. _backgroundGroup lives inside window_group at the
        // very bottom, so the video ends up above the static wallpaper but
        // strictly below desktop-icon windows and all application windows.
        const bgGroup = Main.layoutManager._backgroundGroup;
        const layer = new Clutter.Actor({reactive: false, opacity:0});
        this._rendererLayer = layer;
        const parent = actor.get_parent();
        if (parent)
            parent.remove_child(actor);
        bgGroup.add_child(layer);
        layer.add_child(actor);

        // The shell recreates its static background actors whenever settings,
        // monitors, or the session mode change (including right after the
        // login transition), and new ones are added on top of the group -
        // which would bury the video under the static wallpaper. Pin our
        // actor to the top of the group whenever a sibling appears.
        bgGroup.set_child_above_sibling(layer, null);
        this._bgChildAddedId = bgGroup.connect('child-added', (group, child) => {
            if (child !== layer)
                group.set_child_above_sibling(layer, null);
        });

        // Mutter positions normal windows below the panel. Keep the wallpaper
        // painting at the monitor origin without making the window fullscreen
        // (which would hide the user's panel/Dock).
        const alignActor = () => {
            // Shell's map animation resets the window actor's translation.
            // Keep the offset on our own parent, independent of that animation.
            if (Number.isFinite(actor.x) && Number.isFinite(actor.y))
                layer.set_position(geo.x - actor.x, geo.y - actor.y);
        };
        this._rendererGeometryIds = ['notify::x', 'notify::y'].map(signal => actor.connect(signal, alignActor));
        alignActor();
        actor.show();

        this._rendererUnmanagedId = window.connect('unmanaged', () => {
            this._forgetWindow();
        });

        // A wallpaper must never hold focus or rise in the stack, yet its
        // surface covers the whole desktop, so any click on "the desktop"
        // actually lands on it. Undo both effects whenever they happen -
        // without this, clicking the wallpaper visibly yanks focus off the
        // active application (and Mutter logs stack-position assertions when
        // it tries to restack a window whose actor lives in the background
        // layer).
        this._rendererRaisedId = window.connect_after('raised', () => {
            window.lower();
        });
        this._rendererFocusId = window.connect('focus', () => {
            this._refocusNormalWindow(window);
        });

        // The renderer stole focus when it mapped; give it back to the most
        // recently used normal window.
        this._refocusNormalWindow(window);
        this._startPointerBridge();
        const reveal = () => {
            if (this._rendererActor !== actor || this._procStopping) return;
            if (this._rendererFirstFrameId) {actor.disconnect(this._rendererFirstFrameId); this._rendererFirstFrameId = 0;}
            layer.opacity = 255;
            this._rendererReady = true;
            this._overviewWallpaper ??= new OverviewWallpaper(this);
            this._overviewWallpaper.refresh();
            this._manager?.adopted();
        };
        if (actor.get_texture()?.get_texture()) reveal();
        else this._rendererFirstFrameId = actor.connect('first-frame', reveal);

        console.warn(`[wallpaperengine@waylandwe] adopted renderer window ` +
            `"${window.get_title() ?? ''}" (pid ${window.get_pid()}) ` +
            `into the background layer`);

        return true;
    }

    _refocusNormalWindow(rendererWindow) {
        const tabList = global.display
            .get_tab_list(Meta.TabList.NORMAL, null)
            .filter(w => w !== rendererWindow && !w.skip_taskbar);
        if (tabList.length > 0)
            tabList[0].activate(global.get_current_time());
        else
            global.display.unset_input_focus(global.get_current_time());
    }

    _forgetWindow() {
        if (this._rendererFirstFrameId && this._rendererActor) {
            this._rendererActor.disconnect(this._rendererFirstFrameId);
            this._rendererFirstFrameId = 0;
        }
        this._rendererReady = false;
        this._overviewWallpaper?.clearSurface();
        for (const id of this._rendererGeometryIds ?? []) {
            try { this._rendererActor?.disconnect(id); } catch (_) { /* Actor disposed. */ }
        }
        this._rendererGeometryIds = [];
        if (this._rendererWindow !== null) {
            if (this._rendererUnmanagedId)
                this._rendererWindow.disconnect(this._rendererUnmanagedId);
            if (this._rendererRaisedId)
                this._rendererWindow.disconnect(this._rendererRaisedId);
            if (this._rendererFocusId)
                this._rendererWindow.disconnect(this._rendererFocusId);

        }
        if (this._bgChildAddedId) {
            Main.layoutManager._backgroundGroup.disconnect(this._bgChildAddedId);
            this._bgChildAddedId = 0;
        }
        if (this._rendererVisibleId && this._rendererActor) {
            try {
                this._rendererActor.disconnect(this._rendererVisibleId);
            } catch (_e) {
                // Actor may already be disposed if this runs from 'unmanaged'.
            }
        }
        this._rendererVisibleId = 0;
        this._rendererUnmanagedId = 0;
        this._rendererRaisedId = 0;
        this._rendererFocusId = 0;
        this._rendererGeometryIds = [];
        const actor = this._rendererActor;
        const layer = this._rendererLayer;
        if (actor && layer && actor.get_parent() === layer) {
            layer.remove_child(actor);
            global.window_group.add_child(actor);
        }
        layer?.destroy();
        this._rendererLayer = null;
        this._rendererWindow = null;
        this._rendererActor = null;
    }

    _releaseWindow() {
        // Return the actor before destroying our positioning container.
        this._forgetWindow();
    }

    _startPointerBridge() {
        this._stopPointerBridge();
        if (this._resolveEngine() !== 'wallpaperengine')
            return;
        this._pointerBridge = new PointerBridge(this._socketPath, () => {
            const [x, y, mask] = global.get_pointer();
            const geo = this._targetGeometry();
            const active = !this._paused && !Main.overview.visible && !Main.screenShield.locked &&
                x >= geo.x && y >= geo.y && x < geo.x + geo.width && y < geo.y + geo.height;
            // Track motion across the desktop, but never forward clicks on apps,
            // panel controls or the Dock into the wallpaper.
            let picked = global.stage.get_actor_at_pos(Clutter.PickMode.REACTIVE, x, y);
            let desktop = false;
            while (picked) {
                if (picked === this._rendererActor || picked === Main.layoutManager._backgroundGroup)
                    desktop = true;
                picked = picked.get_parent();
            }
            return {x: Math.max(0, Math.min(1, (x - geo.x) / geo.width)),
                y: Math.max(0, Math.min(1, (y - geo.y) / geo.height)), active,
                left: active && desktop && Boolean(mask & Clutter.ModifierType.BUTTON1_MASK),
                right: active && desktop && Boolean(mask & Clutter.ModifierType.BUTTON3_MASK)};
        });
    }

    _stopPointerBridge() {
        this._pointerBridge?.stop();
        this._pointerBridge = null;
    }

    // ---------------------------------------------------------------- misc

    _notifyError(message) {
        this._manager?.failed(message);
        console.error(`[wallpaperengine@waylandwe] ${message}`);
        Main.notify('Wallpaper Engine for Wayland', message);
    }
}
