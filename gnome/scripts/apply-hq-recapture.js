// Explicit Looking Glass update of manager methods only; no Shell/renderer restart.
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {WallpaperManager} from '../../runtime/hq-recapture-live/manager.js';
import {RuntimeCapture} from '../../runtime/hq-recapture-live/runtimeCapture.js';
export function apply() {
    const ext=Main.extensionManager.lookup('wallpaperengine@waylandwe')?.stateObj;
    const manager=ext?._manager;
    if(!manager || manager.dead)throw new Error('请先启用壁纸管理扩展');
    if(manager.capture || manager.runtimeCapture?.job)throw new Error('请等待当前截图任务结束后再更新');
    const prototype=Object.getPrototypeOf(manager);
    // Older constructors do not initialise RuntimeCapture. Lazy creation also
    // keeps later disable/enable cycles within this cached Shell module working.
    Object.defineProperty(prototype,'runtimeCapture',{
        configurable:true,
        get(){return this._runtimeCapture ??= new RuntimeCapture(this);},
        set(value){this._runtimeCapture=value;},
    });
    for(const key of Object.getOwnPropertyNames(WallpaperManager.prototype)) {
        if(key!=='constructor')Object.defineProperty(prototype,key,Object.getOwnPropertyDescriptor(WallpaperManager.prototype,key));
    }
    manager.runtimeCapture=new RuntimeCapture(manager);
    manager.publish();
    return '独立 4K 高质量截图功能已启用；请重新打开壁纸管理界面。当前模式、壁纸和帧率未改变。';
}
