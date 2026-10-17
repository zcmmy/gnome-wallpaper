// A native still behind the app grid; allocated only while overview is open.
// No renderer process, pixel copies, timer or per-frame callbacks.
import Clutter from 'gi://Clutter';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Background from 'resource:///org/gnome/shell/ui/background.js';

export class StaticOverview {
    constructor(extension) {
        this.extension = extension;
        this.group = null;
        this.backgrounds = [];
        this.showing = Main.overview.visible;
        this.dead = false;
        this.signals = [
            [Main.overview, Main.overview.connect('showing', () => {this.showing = true; this.sync();})],
            [Main.overview, Main.overview.connect('hidden', () => {this.showing = false; this.clear();})],
            [Main.layoutManager, Main.layoutManager.connect('monitors-changed', () => {this.clear(); this.sync();})],
        ];
        this.sync();
    }
    sync() {
        if (this.dead) return;
        if (!this.showing || this.extension._rendererReady) {this.clear(); return;}
        if (this.group || !Main.layoutManager.monitors.length) return;
        this.group = new Clutter.Actor({name:'wallpaper-static-overview', reactive:false,
            x:0, y:0, width:global.stage.width, height:global.stage.height});
        Main.layoutManager.overviewGroup.insert_child_at_index(this.group, 0);
        for (let index = 0; index < Main.layoutManager.monitors.length; index++) {
            const manager = new Background.BackgroundManager({container:this.group,
                monitorIndex:index, vignette:true, controlPosition:true});
            this.backgrounds.push(manager);
        }
    }
    clear() {
        for (const manager of this.backgrounds) manager.destroy();
        this.backgrounds = [];
        this.group?.destroy();
        this.group = null;
    }
    snapshot() {
        return {active:!!this.group, mapped:this.group?.mapped ?? false,
            backgrounds:this.backgrounds.map(manager => {
                const actor = manager.backgroundActor;
                const [width,height] = actor.get_transformed_size();
                return {monitor:actor.monitor,width,height,mapped:actor.mapped,
                    loaded:actor.content.background.isLoaded};
            })};
    }
    destroy() {
        if (this.dead) return;
        this.dead = true;
        for (const [object,id] of this.signals) object.disconnect(id);
        this.signals = [];
        this.clear();
    }
}
