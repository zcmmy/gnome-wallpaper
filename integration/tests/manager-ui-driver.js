import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {fillManagerWindow} from '../../gnome/extension/managerUi.js';
const settings=new Gio.Settings({schema_id:'org.gnome.shell.extensions.wallpaperengine'});
const app=new Adw.Application({application_id:'io.github.wallpaperadapter.UiTest'});
const assert=(v,m)=>{if(!v)throw new Error(m);};
app.connect('activate',()=>{
 const window=new Adw.PreferencesWindow({application:app});const ui=fillManagerWindow(window,settings);window.present();let tick=0;
 const capture=name=>GLib.timeout_add(GLib.PRIORITY_DEFAULT,400,()=>{Gio.DBus.session.call('org.gnome.Shell','/org/gnome/Shell/WallpaperUiTest','org.wallpaper.UiTest','Capture',new GLib.Variant('(s)',[name]),new GLib.VariantType('(s)'),0,5000,null,(bus,result)=>{try{bus.call_finish(result);}catch(e){console.error('UI-TEST ERROR capture '+e.message);}});return GLib.SOURCE_REMOVE;});
 GLib.timeout_add(GLib.PRIORITY_DEFAULT,1000,()=>{
  try{
   tick++;
   if(tick===3){assert(ui.model.items.length===7,'library count');assert(ui.importButton.label==='导入壁纸…'&&ui.removeButton.label==='删除壁纸…','file controls missing');assert(ui.model.connected,'controller not connected');ui.search.text='拉特兰';ui.flow.invalidate_filter();console.log('UI-TEST library connected');}
   if(tick===4){ui.search.text='';let row=ui.flow.get_first_child();while(row&&row._item.id!=='3582858114')row=row.get_next_sibling();ui.flow.select_child(row);ui.apply.emit('clicked');}
   if(tick===5){assert(settings.get_string('selected-id')==='3582858114','apply action');assert(!settings.get_boolean('enabled'),'preview enabled renderer');capture('ui-library');}
   if(tick===7){window.set_visible_page(ui.pages[2]);ui.fps.set_value(15);capture('ui-settings');}
   if(tick===10){window.set_visible_page(ui.pages[1]);ui.sequence.selected=1;ui.interval.set_value(30);ui.rotate.active=true;capture('ui-rotation');ui.all.active=false;}
   if(tick===11){const findCheck=w=>{if(w instanceof Gtk.CheckButton)return w;for(let c=w.get_first_child();c;c=c.get_next_sibling()){const found=findCheck(c);if(found)return found;}return null;};let row=ui.rotationList.get_first_child();findCheck(row).active=true;findCheck(row.get_next_sibling()).active=true;}
   if(tick===12){assert(settings.get_strv('rotation-ids').length===2,'custom participation checkboxes');ui.all.active=true;assert(settings.get_boolean('rotation-enabled')&&settings.get_string('rotation-mode')==='shuffle','rotation controls');ui.rotate.active=false;window.set_visible_page(ui.pages[0]);ui.mode.active=true;}
   if(tick===18){const status=JSON.parse(settings.get_string('runtime-status'));assert(status.state==='dynamic'&&status.pid,'UI dynamic mode failed: '+JSON.stringify(status));ui.mode.active=false;}
   if(tick===21){const status=JSON.parse(settings.get_string('runtime-status'));assert(!status.pid&&status.state==='static','UI stop mode failed');console.log('UI-TEST PASS: gallery/apply/fps/rotation/mode controls and teardown');window.close();app.quit();return GLib.SOURCE_REMOVE;}
  }catch(e){console.error('UI-TEST ERROR '+e.message+' '+e.stack);window.close();app.quit();return GLib.SOURCE_REMOVE;}
  return GLib.SOURCE_CONTINUE;
 });
});app.run([]);
