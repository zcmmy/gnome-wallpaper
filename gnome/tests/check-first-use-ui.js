import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {fillManagerWindow} from '../extension/managerUi.js';
import {paths} from '../extension/common/paths.js';
import {resourceOperation} from '../extension/resourceSetup.js';
const app=new Adw.Application({application_id:'io.github.wallpaperadapter.FirstUseTest'});
const assert=(v,m)=>{if(!v)throw new Error(m);};
app.connect('activate',()=>{
    const settings=new Gio.Settings({schema_id:'org.gnome.shell.extensions.wallpaperengine'});
    const window=new Adw.PreferencesWindow({application:app});
    const ui=fillManagerWindow(window,settings);window.present();
    (async()=>{
        assert(ui.setupGroup.visible,'Empty library has no import guidance');
        assert(!ui.model.items.length&&!settings.get_boolean('enabled'),'First use imported or played automatically');
        assert(settings.get_int('fps')===15&&!settings.get_boolean('rotation-enabled'),'First use changed defaults');
        const fixture=GLib.getenv('TEST_FIXTURE');
        await resourceOperation({operation:'assets',assets:fixture+'/assets'});
        ui.reload();assert(ui.setupGroup.visible,'Guidance hidden before wallpaper import');
        await resourceOperation({operation:'import',source:fixture+'/wallpaper'});
        ui.reload();assert(!ui.setupGroup.visible&&ui.model.items.length===1,'Guidance not dismissed after both imports');
        assert(!settings.get_string('selected-id')&&!settings.get_boolean('enabled'),'Import changed selection or playback');
        assert(settings.get_string('library-root')===paths.library,'Wrong managed library');
        print('FIRST-USE-UI PASS');
    })().catch(e=>{printerr('FIRST-USE-UI ERROR '+e.message+' '+e.stack);}).finally(()=>{window.close();app.quit();});
});
app.run([]);
