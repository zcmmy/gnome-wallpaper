import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {fillManagerWindow} from './managerUi.js';
import {resourceOperation} from './resourceSetup.js';
import {paths} from './common/paths.js';
const app=new Adw.Application({application_id:'io.github.wallpaperadapter.PackageTest'});
app.connect('activate',()=>{
    const settings=new Gio.Settings({schema_id:'org.gnome.shell.extensions.wallpaperengine'});
    const window=new Adw.PreferencesWindow({application:app});const ui=fillManagerWindow(window,settings);window.present();
    GLib.timeout_add(0,1000,()=>{
        (async()=>{
            const assert=(v,m)=>{if(!v)throw new Error(m);};
            assert(ui.model.items.length>0,'No imported wallpapers');
            assert(settings.get_string('library-root')===paths.library,'Wrong library');
            assert(ui.resourceSetup.backend.subtitle.startsWith('已内置'),'Backend preparation status');
            const status=await resourceOperation({operation:'status'});assert(status.assets&&status.entries>0,'Resource status failed');
            assert(!settings.get_boolean('enabled'),'UI enabled animation');
            GLib.file_set_contents(GLib.getenv('TEST_PROFILE')+'/ui-result.json',JSON.stringify({ok:true,items:ui.model.items.length,assets:status.assets}));
        })().catch(e=>GLib.file_set_contents(GLib.getenv('TEST_PROFILE')+'/ui-result.json',JSON.stringify({ok:false,error:e.message}))).finally(()=>{window.close();app.quit();});
        return false;
    });
});app.run([]);
