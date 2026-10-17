import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import {fillManagerWindow} from './managerUi.js';
export default class WallpaperPrefs extends ExtensionPreferences {
    fillPreferencesWindow(window) {fillManagerWindow(window, this.getSettings());}
}
