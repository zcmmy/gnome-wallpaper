// Reuse the renderer surface in Shell's separate overview scene graph.
// No extra renderer, background setting, panel style or Dock setting is needed.
import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Meta from 'gi://Meta';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as Background from 'resource:///org/gnome/shell/ui/background.js';
import {WorkspaceBackground} from 'resource:///org/gnome/shell/ui/workspace.js';
import {WorkspaceThumbnail} from 'resource:///org/gnome/shell/ui/workspaceThumbnail.js';
import {InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

const DECLARATIONS = `uniform sampler2D tex;
uniform float width, height, left, top, right, bottom, radius;`;
const BODY = `
vec2 uv = cogl_tex_coord_in[0].xy;
vec2 p = uv * vec2(width, height);
vec2 halfSize = vec2(right-left, bottom-top) * 0.5;
vec2 q = abs(p - vec2(left+right, top+bottom)*0.5) - halfSize + radius;
float d = length(max(q, vec2(0.0))) + min(max(q.x,q.y),0.0) - radius;
float coverage = 1.0 - smoothstep(-0.5,0.5,d);
cogl_color_out = texture2D(tex,uv) * cogl_color_in * coverage;`;
const snippetAPI = typeof Clutter.ShaderEffect.new_with_snippet === 'function';
class ClipEffectImpl extends Clutter.ShaderEffect {
    _init(background, monitorIndex) {
        super._init();
        this._background = background;
        this._monitorIndex = monitorIndex;
        if (!snippetAPI)
            this.set_shader_source(DECLARATIONS + '\nvoid main() {' + BODY + '}');
    }
    vfunc_paint_target(node, context) {
        const m = Main.layoutManager.monitors[this._monitorIndex];
        const w = Main.layoutManager.getWorkAreaForMonitor(this._monitorIndex);
        const values = {width:m.width, height:m.height, left:w.x-m.x, top:w.y-m.y,
            right:w.x-m.x+w.width, bottom:w.y-m.y+w.height,
            radius:this._background.content.rounded_clip_radius};
        for (const [key, number] of Object.entries(values)) {
            const value = new GObject.Value();
            value.init(GObject.TYPE_FLOAT);
            value.set_float(number);
            this.set_uniform_value(key, value);
        }
        super.vfunc_paint_target(node, context);
    }
}
if (snippetAPI) {
    ClipEffectImpl.prototype.vfunc_get_static_snippet = function () {
        const snippet = Cogl.Snippet.new(Cogl.SnippetHook.FRAGMENT, DECLARATIONS, null);
        snippet.set_replace(BODY);
        return snippet;
    };
}
const ClipEffect = GObject.registerClass({GTypeName:'WallpaperAdapterOverviewClip'}, ClipEffectImpl);

// A clone must never contribute its full-screen natural size to the workspace
// layout; that makes app-grid workspace previews expand into horizontal strips.
const Surface = GObject.registerClass({GTypeName:'WallpaperAdapterOverviewSurface'},
class Surface extends Clutter.Actor {
    _init(source) {
        super._init({name:'wallpaper-overview-clone', reactive:false, clip_to_allocation:true});
        this.source = source;
        this._clone = new Clutter.Clone({source, reactive:false});
        this.add_child(this._clone);
        source.connectObject('notify::width', () => this.queue_relayout(),
            'notify::height', () => this.queue_relayout(), this);
    }
    vfunc_get_preferred_width(_height) {return [0, 0];}
    vfunc_get_preferred_height(_width) {return [0, 0];}
    vfunc_allocate(box) {
        this.set_allocation(box);
        const width = box.get_width(), height = box.get_height();
        // The first Wayland buffer can arrive after adoption/overview layout.
        // Never divide by an unallocated source; retry when its size is known.
        if (![width, height, this.source.width, this.source.height].every(v => Number.isFinite(v) && v > 0)) {
            this._clone.allocate(new Clutter.ActorBox({x1:0, y1:0, x2:0, y2:0}));
            return;
        }
        const scale = Math.max(width / this.source.width, height / this.source.height);
        const cw = this.source.width * scale, ch = this.source.height * scale;
        const childBox = new Clutter.ActorBox({x1:(width-cw)/2, y1:(height-ch)/2,
            x2:(width+cw)/2, y2:(height+ch)/2});
        this._clone.allocate(childBox);
    }
});

export class OverviewWallpaper {
    constructor(extension) {
        this._extension = extension;
        this._records = new Map();
        this._idle = 0;
        this._backdrop = null;
        this._injections = new InjectionManager();
        const self = this;
        this._injections.overrideMethod(Background.BackgroundManager.prototype, '_createBackgroundActor',
            original => function (...args) {
                const actor = original.apply(this, args);
                self._queueRefresh();
                return actor;
            });
        this._injections.overrideMethod(WorkspaceThumbnail.prototype, '_init',
            original => function (...args) {
                original.apply(this, args);
                self._queueRefresh();
            });
        this._showId = Main.overview.connect('showing', () => this._queueRefresh());
        this._queueRefresh();
    }
    _queueRefresh() {
        if (this._idle) return;
        this._idle = GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
            this._idle = 0;
            this.refresh();
            return GLib.SOURCE_REMOVE;
        });
    }
    refresh() {
        const source = this._extension._rendererActor;
        if (!source) {this.clearSurface(); return;}
        if (this._source !== source) {
            this.clearSurface();
            this._source = source;
        }
        const index = this._extension._targetMonitorIndex();
        const monitor = Main.layoutManager.monitors[index];
        if (!this._backdrop) {
            this._backdrop = new Clutter.Actor({name:'wallpaper-overview-backdrop', reactive:false,
                x:monitor.x, y:monitor.y, width:monitor.width, height:monitor.height,
                clip_to_allocation:true});
            const clone = new Clutter.Clone({source, width:monitor.width, height:monitor.height});
            this._backdrop.add_child(clone);
            this._backdrop.add_child(new Clutter.Actor({width:monitor.width,height:monitor.height,
                background_color:new Cogl.Color({red:0,green:0,blue:0,alpha:110})}));
            Main.layoutManager.overviewGroup.insert_child_at_index(this._backdrop, 0);
        }
        const visit = (actor, workspaceBackground = null) => {
            if (actor === this._backdrop || actor.name === 'wallpaper-overview-clone') return;
            if (actor instanceof WorkspaceBackground) workspaceBackground = actor;
            if (actor instanceof Meta.BackgroundActor && actor.monitor === index)
                this._attach(actor, source, workspaceBackground !== null, index);
            if (actor instanceof WorkspaceThumbnail && actor.monitorIndex === index)
                this._attachThumbnail(actor, source, monitor);
            for (const child of actor.get_children()) visit(child, workspaceBackground);
        };
        visit(Main.layoutManager.overviewGroup);
    }
    _track(actor, clone) {
        const record = {clone, signals:[]};
        this._records.set(actor, record);
        record.signals.push(actor.connect('destroy', () => this._records.delete(actor)));
        return record;
    }
    _attach(actor, source, rounded, index) {
        if (this._records.has(actor)) return;
        const wrapper = new Surface(source);
        wrapper.add_constraint(new Clutter.BindConstraint({source:actor, coordinate:Clutter.BindCoordinate.SIZE}));
        if (rounded) wrapper.add_effect(new ClipEffect(actor, index));
        actor.add_child(wrapper);
        this._track(actor, wrapper);
    }
    _attachThumbnail(actor, source, monitor) {
        if (this._records.has(actor)) return;
        const clone = new Surface(source);
        clone.set_position(monitor.x, monitor.y);
        clone.set_size(monitor.width, monitor.height);
        actor._contents.insert_child_at_index(clone, 0);
        this._track(actor, clone);
    }
    clearSurface() {
        for (const [actor, record] of this._records) {
            for (const id of record.signals) actor.disconnect(id);
            record.clone.destroy();
        }
        this._records.clear();
        this._backdrop?.destroy();
        this._backdrop = null;
        this._source = null;
    }
    snapshot() {
        const bounds = actor => {
            const [x,y] = actor.get_transformed_position();
            const [width,height] = actor.get_transformed_size();
            return {x,y,width,height,mapped:actor.mapped};
        };
        return {backdrop:this._backdrop ? bounds(this._backdrop):null,
            clones:[...this._records].map(([actor,r]) => ({target:String(actor),
                sourceMatches:(r.source ?? r.clone.source) === this._extension._rendererActor,
                bounds:bounds(r.clone)}))};
    }
    destroy() {
        if (this._idle) GLib.source_remove(this._idle);
        this._idle = 0;
        Main.overview.disconnect(this._showId);
        this._injections.clear();
        this.clearSurface();
    }
}
