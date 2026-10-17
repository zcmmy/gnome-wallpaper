import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import {fillManagerWindow} from './managerUi.js';
const source=Gio.SettingsSchemaSource.new_from_directory(Gio.File.new_for_uri(import.meta.url).get_parent().get_child('schemas').get_path(),Gio.SettingsSchemaSource.get_default(),false);
const settings=new Gio.Settings({settings_schema:source.lookup('org.gnome.shell.extensions.wallpaperengine',false)});
const app=new Adw.Application({application_id:'io.github.wallpaperadapter.Manager'});
app.connect('activate',()=>{if(app.active_window){app.active_window.present();return;}const window=new Adw.PreferencesWindow({application:app});fillManagerWindow(window,settings);window.present();});
app.run(ARGV);
