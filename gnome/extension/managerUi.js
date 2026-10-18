import Adw from 'gi://Adw';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GdkPixbuf from 'gi://GdkPixbuf';
import {readLibrary, replaceStaticImage, imageInfo} from './library.js';
import {fileOperation, deleteWallpaper, refreshFiles} from './libraryOps.js';
import {restoreStaticWallpaper} from './staticWallpaper.js';

function button(label, callback, style = null) {
    const widget = new Gtk.Button({label, valign:Gtk.Align.CENTER});
    if (style) widget.add_css_class(style);
    widget.connect('clicked', callback);
    return widget;
}
function picture(file, width, height) {
    const widget = new Gtk.Picture({can_shrink:true, content_fit:Gtk.ContentFit.CONTAIN});
    if (file) {
        try {widget.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(file,width,height,true));} catch (_) {}
    }
    return widget;
}
function label(text, css = null) {
    const w = new Gtk.Label({label:text, xalign:0, wrap:true});
    if (css) w.add_css_class(css);
    return w;
}
function infoPath(item, thumb = false) {
    if (item.ready) {
        if (thumb) {
            try {
                const a=Gio.File.new_for_path(item.still).query_info('time::modified',0,null);
                const b=Gio.File.new_for_path(item.thumbnail).query_info('time::modified',0,null);
                if (b.get_attribute_uint64('time::modified') >= a.get_attribute_uint64('time::modified')) return item.thumbnail;
            } catch (_) {}
        }
        return item.still;
    }
    return item.preview;
}

export function fillManagerWindow(window, settings) {
    window.set_title('壁纸管理'); window.set_default_size(1080, 800);
    window.set_search_enabled(false);
    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_DARK);
    window.set_size_request(960, 640);
    const signals = [];
    const model = {items:[], selected:null, connected:false, closed:false};
    let busy=false;
    async function mutate(action) {
        if(busy)return;
        busy=true;window.set_sensitive(false);window.set_title('壁纸管理 — 正在处理文件…');
        try{await action();}catch(e){toast(e.message);}finally{busy=false;if(!model.closed){window.set_sensitive(true);window.set_title('壁纸管理');reload();}}
    }
    const toast = message => window.add_toast(new Adw.Toast({title:message, timeout:5}));
    const watch = (key, callback) => signals.push(settings.connect('changed::'+key, callback));
    const page = new Adw.PreferencesPage({title:'壁纸库', icon_name:'preferences-desktop-wallpaper-symbolic'});
    const rotationPage = new Adw.PreferencesPage({title:'轮换', icon_name:'media-playlist-repeat-symbolic'});
    const options = new Adw.PreferencesPage({title:'设置', icon_name:'preferences-system-symbolic'});
    window.add(page); window.add(rotationPage); window.add(options);
    // PreferencesPage normally clamps forms to ~600px. The gallery needs a
    // wider canvas; keep the two ordinary settings pages at their native width.
    const widen = widget => {
        if (widget instanceof Adw.Clamp || widget instanceof Adw.ClampScrollable) {
            widget.set_maximum_size(1040); widget.set_tightening_threshold(960);
        }
        for (let child=widget.get_first_child();child;child=child.get_next_sibling()) widen(child);
    };
    widen(page);

    const stateGroup = new Adw.PreferencesGroup({title:'桌面壁纸'}); page.add(stateGroup);
    const stateRow = new Adw.ActionRow({title:'静态模式', subtitle:'选择壁纸后点击应用；浏览图片不会改变桌面。'});
    const mode = new Gtk.Switch({valign:Gtk.Align.CENTER, tooltip_text:'开启动态后，后续切换和轮换继续使用动态模式'});
    mode.set_active(settings.get_boolean('enabled'));
    let syncing = false;
    mode.connect('notify::active', () => {
        if (syncing) return;
        if (!model.connected) {syncing=true; mode.set_active(false); syncing=false; toast('请先启用新版壁纸扩展。'); return;}
        settings.set_boolean('enabled', mode.active);
    });
    stateRow.add_suffix(mode); stateGroup.add(stateRow);
    const actions = new Gtk.Box({spacing:8});
    const dispatch = cmd => settings.set_string('manager-command', cmd+':'+GLib.uuid_string_random());
    actions.append(button('上一张', () => dispatch('previous')));
    actions.append(button('下一张', () => dispatch('next')));
    actions.append(button('重试动态', () => {if (settings.get_boolean('enabled')) dispatch('retry'); else settings.set_boolean('enabled',true);}));
    const refresh = button('刷新壁纸库', () => settings.set_int('library-revision',(settings.get_int('library-revision')+1)%2147483647));
    actions.append(refresh); stateGroup.add(actions);

    const gallery = new Adw.PreferencesGroup({title:'本地壁纸'}); page.add(gallery);
    const search = new Gtk.SearchEntry({placeholder_text:'搜索名称或 Workshop ID', hexpand:true});
    const filter = new Gtk.DropDown({model:Gtk.StringList.new(['全部','场景','视频','缺少静态图'])});
    const searchRow = new Gtk.Box({spacing:8}); searchRow.append(search); searchRow.append(filter); gallery.add(searchRow);
    const importRow=new Gtk.Box({spacing:8,margin_top:8});
    const importButton=button('导入壁纸…',()=>new Gtk.FileDialog({title:'选择单张壁纸目录，或包含多张壁纸的目录'}).select_folder(window,null,(dialog,result)=>{
        let path;try{path=dialog.select_folder_finish(result)?.get_path();}catch(_){return;}if(!path)return;
        mutate(async()=>{
            const result=await fileOperation('import',settings.get_string('library-root'),path);
            refreshFiles(settings);
            toast(`导入 ${result.imported.length} 张，跳过已有 ${result.skipped.length} 张，失败 ${result.errors.length} 张`);
            if(result.errors.length){const info=new Adw.AlertDialog({heading:'部分壁纸未能导入',body:result.errors.map(e=>e.id+'：'+e.message).join('\n')});info.add_response('ok','知道了');info.present(window);}
        });
    }));importRow.append(importButton);importRow.append(label('复制到壁纸库，保留原文件；已有同名目录会跳过。','dim-label'));gallery.add(importRow);
    const body = new Gtk.Box({spacing:20, homogeneous:true, margin_top:12, valign:Gtk.Align.START}); gallery.add(body);
    const flow = new Gtk.FlowBox({selection_mode:Gtk.SelectionMode.SINGLE, max_children_per_line:2, min_children_per_line:2, homogeneous:true, row_spacing:8, column_spacing:8, valign:Gtk.Align.START, activate_on_single_click:true});
    const scroller = new Gtk.ScrolledWindow({child:flow, hscrollbar_policy:Gtk.PolicyType.NEVER, min_content_height:470, max_content_height:620, vexpand:true, hexpand:true});
    body.append(scroller);
    const detail = new Gtk.Box({orientation:Gtk.Orientation.VERTICAL, spacing:12, width_request:380, valign:Gtk.Align.START}); body.append(detail);
    const preview = picture(null,760,428);
    const previewFrame = new Gtk.AspectFrame({ratio:16/9, obey_child:false, child:preview});
    detail.append(previewFrame);
    const title = label('选择一张壁纸', 'title-3'); title.set_max_width_chars(35); detail.append(title);
    const description = label('', 'dim-label'); detail.append(description);
    const missing = label(''); detail.append(missing);
    const apply = button('应用壁纸', () => {
        const item = model.selected;
        if (!item) return;
        if (!model.connected) {toast('请先启用新版壁纸扩展。');return;}
        if (settings.get_string('selected-id') === item.id) dispatch('retry');
        else settings.set_string('selected-id', item.id);
        updateStatus();
    }, 'suggested-action'); detail.append(apply);
    const capture = button('开启动态并生成静态图', () => {
        const item = model.selected;
        if (!item || !model.connected) return;
        // Mode is enabled only by this explicit user action. Select first so a
        // previously static desktop never launches the old wallpaper briefly.
        settings.set_string('selected-id',item.id);
        if (settings.get_boolean('enabled')) dispatch('retry');
        else settings.set_boolean('enabled', true);
    }); detail.append(capture);
    let lastCaptureResult = null;
    try {lastCaptureResult=JSON.parse(settings.get_string('runtime-status')).runtimeCapture?.request ?? null;} catch (_) {}
    const runtimeCapture = button('高质量截图并替换静态图…', () => {
        const item=model.selected;
        if(!item || !model.connected)return;
        const dialog=new Adw.AlertDialog({heading:'用高质量截图替换静态图？',body:'将为「'+item.title+'」另开一次高质量截图任务，成功后覆盖其静态图片。场景以 4K 渲染后缩小至 1080p；视频按原始画面采样。动态播放继续，帧率设置不变。截图时刻可能与桌面不同，任务期间会额外占用资源。'});
        dialog.add_response('cancel','取消');dialog.add_response('capture','截图并替换');
        dialog.set_close_response('cancel');dialog.set_response_appearance('capture',Adw.ResponseAppearance.DESTRUCTIVE);
        dialog.choose(window,null,(dlg,res)=>{
            if(dlg.choose_finish(res)!=='capture')return;
            if(settings.get_string('selected-id')!==item.id){toast('当前壁纸已切换，未截图。');return;}
            settings.set_string('manager-command',JSON.stringify({action:'capture-static',id:item.id,request:GLib.uuid_string_random()}));
        });
    });
    runtimeCapture.set_tooltip_text('后台独立生成高质量静态图；播放继续，截图时刻可能不同。');detail.append(runtimeCapture);
    function updateCaptureAction(status) {
        runtimeCapture.set_sensitive(model.connected && status.runtimeCaptureSupported===true && status.runtimeCaptureQuality==='4k-to-1080p' && status.state==='dynamic' &&
            !status.capturing && !!model.selected?.supported && model.selected.id===settings.get_string('selected-id'));
    }
    const replace = button('选择静态图片…', () => {
        const item = model.selected;
        if (!item) return;
        const images = new Gtk.FileFilter(); images.set_name('图片'); images.add_pixbuf_formats();
        const filters = new Gio.ListStore({item_type:Gtk.FileFilter}); filters.append(images);
        new Gtk.FileDialog({title:'选择图片替换「'+item.title+'」的静态背景', filters}).open(window,null,(dialog,result) => {
            try {
                const file = dialog.open_finish(result);
                if (!file?.get_path()) return;
                replaceStaticImage(item.path,file.get_path());
                settings.set_int('static-revision',(settings.get_int('static-revision')+1)%2147483647);
                toast('已保存静态图片；后续辅助截图不会覆盖它。');
            } catch (e) {if (!e.matches?.(Gtk.DialogError, Gtk.DialogError.DISMISSED)) toast('未替换图片：'+e.message);}
        });
    }); detail.append(replace);
    const removeButton=button('删除壁纸…',()=>{
        const item=model.selected;if(!item)return;
        const dialog=new Adw.AlertDialog({heading:'删除这张壁纸？',body:'「'+item.title+'」将从壁纸库移到系统回收站。若正在使用，会先切换到其他壁纸；最后一张会保留静态背景。'});
        dialog.add_response('cancel','取消');dialog.add_response('delete','移到回收站');dialog.set_response_appearance('delete',Adw.ResponseAppearance.DESTRUCTIVE);dialog.set_close_response('cancel');
        dialog.choose(window,null,(dlg,res)=>{if(dlg.choose_finish(res)==='delete')mutate(async()=>{await deleteWallpaper(settings,item.id,model.connected);toast('壁纸已移到回收站');});});
    });detail.append(removeButton);
    detail.append(label('静态图保存在壁纸目录的 static-background.png，可自行替换。已有图片不会自动覆盖。','dim-label'));

    function show(item) {
        model.selected=item;
        title.set_label(item?.title ?? '壁纸库为空');
        description.set_label(item ? `${item.type === 'video' ? '视频' : '场景'} · ${item.id}` : '在设置中选择包含 project.json 子目录的壁纸库。');
        preview.set_paintable(null);
        if (item) {try {preview.set_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(infoPath(item),760,428,true));} catch (_) {}}
        missing.set_label(item ? (item.ready ? '静态图片已准备，可直接应用。' : '当前展示作者预览图。缺少完整静态图片，可自行指定，或开启动态后自动截图一次。') + (item.warning ? '\n'+item.warning : '') : '');
        apply.set_sensitive(!!item && model.connected);
        replace.set_sensitive(!!item);removeButton.set_sensitive(!!item);
        capture.set_visible(!!item && !item.ready && item.supported);
        capture.set_sensitive(model.connected);
        let status={};try{status=JSON.parse(settings.get_string('runtime-status'));}catch(_){}
        updateCaptureAction(status);
    }
    flow.connect('selected-children-changed', () => {const child=flow.get_selected_children()[0];if(child)show(child._item);});
    flow.set_filter_func(child => {
        const i=child._item, term=search.text.trim().toLocaleLowerCase(), kind=filter.selected;
        return (!term || (i.title+' '+i.id).toLocaleLowerCase().includes(term)) &&
            (kind===0 || kind===1&&i.type==='scene' || kind===2&&i.type==='video' || kind===3&&!i.ready);
    });
    search.connect('search-changed',()=>flow.invalidate_filter()); filter.connect('notify::selected',()=>flow.invalidate_filter());
    function reload() {
        const selected=model.selected?.id ?? settings.get_string('selected-id');
        try {model.items=readLibrary(settings.get_string('library-root'));} catch(e) {model.items=[];toast('读取壁纸库失败：'+e.message);}
        let child;while((child=flow.get_first_child()))flow.remove(child);
        for (const item of model.items) {
            const box = new Gtk.Box({orientation:Gtk.Orientation.VERTICAL,spacing:6, margin_top:6,margin_bottom:6,margin_start:6,margin_end:6,width_request:200});
            const thumb = picture(infoPath(item,true),320,180);
            box.append(new Gtk.AspectFrame({ratio:16/9,obey_child:false,child:thumb,height_request:112}));
            box.append(new Gtk.Label({label:item.title,xalign:0,ellipsize:3,max_width_chars:16,tooltip_text:item.title}));
            box.append(new Gtk.Label({label:(item.type==='video'?'视频':'场景')+' · '+(item.ready?'静态已准备':'需准备静态图'),xalign:0,css_classes:['dim-label']}));
            const row = new Gtk.FlowBoxChild({child:box});row._item=item;flow.insert(row,-1);
            if(item.id===selected)flow.select_child(row);
        }
        if (!flow.get_selected_children().length && flow.get_first_child())flow.select_child(flow.get_first_child());
        if(!model.items.length)show(null);
        gallery.set_title(`本地壁纸 · ${model.items.length} 张`);
        rebuildRotation(); updateStatus();
    }
    function updateStatus() {
        let status={};try{status=JSON.parse(settings.get_string('runtime-status'));}catch(_){}
        if(status.active === false)model.connected=false;
        const names={static:'静态模式',dynamic:'动态模式',loading:'动态加载中',stopping:'正在停止动态',error:'需要处理',disabled:'扩展未启用'};
        stateRow.set_title(model.connected ? names[status.state] ?? '壁纸管理' : '扩展未启用或需要更新');
        stateRow.set_subtitle(model.connected ? (status.error || (status.capturing?'正在生成一次静态截图…':`当前：${model.items.find(i=>i.id===settings.get_string('selected-id'))?.title ?? '未选择'} · ${settings.get_int('fps')} FPS 上限`)) : '预览和静态图替换可用；启用新版扩展后可应用、轮换与播放。');
        syncing=true;mode.set_active(settings.get_boolean('enabled'));syncing=false;
        mode.set_sensitive(model.connected); actions.set_sensitive(model.connected); refresh.set_sensitive(true);
        if(model.selected){apply.set_sensitive(model.connected);capture.set_sensitive(model.connected);}
        updateCaptureAction(status);
        const result=status.runtimeCapture;
        if(result?.request && result.state!=='capturing' && lastCaptureResult!==result.request){
            lastCaptureResult=result.request;if(result.message)toast(result.message);
        }
        updateDeadline();
    }

    const rotationGroup = new Adw.PreferencesGroup({title:'定时切换',description:'关闭管理窗口后仍按计划切换。关闭扩展后停止；动态模式沿用当前开关。'}); rotationPage.add(rotationGroup);
    const rotate = new Adw.SwitchRow({title:'启用轮换'});settings.bind('rotation-enabled',rotate,'active',Gio.SettingsBindFlags.DEFAULT);rotationGroup.add(rotate);
    const interval = new Adw.SpinRow({title:'切换间隔',subtitle:'分钟',adjustment:new Gtk.Adjustment({lower:1,upper:10080,step_increment:1,page_increment:10})});settings.bind('rotation-interval',interval,'value',Gio.SettingsBindFlags.DEFAULT);rotationGroup.add(interval);
    const sequence = new Adw.ComboRow({title:'切换顺序',model:Gtk.StringList.new(['按列表顺序','伪随机序列（一轮内不重复）'])});
    sequence.selected=settings.get_string('rotation-mode')==='shuffle'?1:0;
    sequence.connect('notify::selected',()=>settings.set_string('rotation-mode',sequence.selected?'shuffle':'ordered'));rotationGroup.add(sequence);
    const deadline = new Adw.ActionRow({title:'下一次切换'});rotationGroup.add(deadline);
    function updateDeadline(){const time=settings.get_double('rotation-next-at');deadline.set_subtitle(settings.get_boolean('rotation-enabled')&&time>0?new Date(time*1000).toLocaleString():'轮换已关闭或可用壁纸不足两张');}
    const all = new Adw.SwitchRow({title:'包括全部已准备的壁纸',subtitle:'关闭后可勾选并调整列表顺序；缺少静态图的壁纸不会自动播放。'});settings.bind('rotation-all',all,'active',Gio.SettingsBindFlags.DEFAULT);rotationGroup.add(all);
    const listGroup = new Adw.PreferencesGroup({title:'参与列表'});rotationPage.add(listGroup);
    const list = new Gtk.ListBox({selection_mode:Gtk.SelectionMode.NONE,css_classes:['boxed-list']});listGroup.add(list);
    let rotationRebuild = 0;
    function scheduleRotationRebuild() {
        if (rotationRebuild) return;
        rotationRebuild=GLib.idle_add(GLib.PRIORITY_DEFAULT,()=>{
            rotationRebuild=0; if(!model.closed)rebuildRotation(); return GLib.SOURCE_REMOVE;
        });
    }
    function rebuildRotation() {
        let node;while((node=list.get_first_child()))list.remove(node);
        const ids=settings.get_strv('rotation-ids'), includeAll=settings.get_boolean('rotation-all');
        const ordered=[...model.items].sort((a,b)=>{const ai=ids.indexOf(a.id),bi=ids.indexOf(b.id);return (ai<0?999:ai)-(bi<0?999:bi);});
        for(const item of ordered){
            const row=new Adw.ActionRow({title:GLib.markup_escape_text(item.title,-1),subtitle:item.ready?item.id:'缺少静态图，暂不参与轮换',title_lines:1});
            const check=new Gtk.CheckButton({active:includeAll&&item.ready || ids.includes(item.id),sensitive:!includeAll&&item.ready,valign:Gtk.Align.CENTER});
            check.connect('toggled',()=>{let value=settings.get_strv('rotation-ids').filter(id=>id!==item.id);if(check.active)value.push(item.id);settings.set_strv('rotation-ids',value);});row.add_prefix(check);
            for(const [text,dir] of [['↑',-1],['↓',1]]){
                const move=button(text,()=>{const value=settings.get_strv('rotation-ids');const index=value.indexOf(item.id), next=index+dir;if(index>=0&&next>=0&&next<value.length){[value[index],value[next]]=[value[next],value[index]];settings.set_strv('rotation-ids',value);}});
                move.set_sensitive(!includeAll&&ids.includes(item.id));row.add_suffix(move);
            }
            list.append(row);
        }
    }
    const playback = new Adw.PreferencesGroup({title:'动态播放',description:'只有明确开启动态后才启动 Portghost。重新登录默认回到静态。'});options.add(playback);
    const fps = new Adw.SpinRow({title:'最大帧率',subtitle:'所有壁纸共用；静态模式仅保存此设置',adjustment:new Gtk.Adjustment({lower:1,upper:240,step_increment:1,page_increment:5})});settings.bind('fps',fps,'value',Gio.SettingsBindFlags.DEFAULT);playback.add(fps);
    const presets=new Gtk.Box({spacing:8});for(const n of [10,15,24,30,60])presets.append(button(n+' FPS',()=>settings.set_int('fps',n)));playback.add(presets);
    const mute=new Adw.SwitchRow({title:'静音',subtitle:'静音不关闭场景的系统音频频谱响应'});settings.bind('mute',mute,'active',Gio.SettingsBindFlags.DEFAULT);playback.add(mute);
    const scaling=new Adw.ComboRow({title:'画面适配',model:Gtk.StringList.new(['填满屏幕（裁剪）','完整显示（留边）','拉伸'])});
    const scales=['fill','fit','stretch'];scaling.selected=Math.max(0,scales.indexOf(settings.get_string('scaling')));scaling.connect('notify::selected',()=>settings.set_string('scaling',scales[scaling.selected]));playback.add(scaling);
    const paths=new Adw.PreferencesGroup({title:'资源与恢复'});options.add(paths);
    const library=new Adw.ActionRow({title:'壁纸库目录',subtitle:settings.get_string('library-root')});
    library.add_suffix(button('选择…',()=>new Gtk.FileDialog({title:'选择壁纸库根目录'}).select_folder(window,null,(dialog,result)=>{try{const file=dialog.select_folder_finish(result);if(file?.get_path())settings.set_string('library-root',file.get_path());}catch(_){}})));paths.add(library);
    for(const [key,text] of [['wallpaperengine-path','Portghost 可执行程序'],['assets-path','Wallpaper Engine 公共资源']]){
        const row=new Adw.EntryRow({title:text,show_apply_button:true});row.text=settings.get_string(key);row.connect('apply',()=>settings.set_string(key,row.text.trim()));paths.add(row);
    }
    const restore=new Adw.ActionRow({title:'恢复最初的 GNOME 壁纸',subtitle:'会关闭动态播放与轮换，保留壁纸库和自定义静态图片。'});
    restore.add_suffix(button('恢复',()=>{
        const dialog=new Adw.AlertDialog({heading:'恢复原来的壁纸？',body:'动态播放与定时轮换将关闭。壁纸库中的图片不会删除。'});
        dialog.add_response('cancel','取消');dialog.add_response('restore','恢复');dialog.set_close_response('cancel');
        dialog.choose(window,null,(dlg,res)=>{if(dlg.choose_finish(res)!=='restore')return;try{settings.set_boolean('rotation-enabled',false);settings.set_boolean('enabled',false);if(!restoreStaticWallpaper())throw new Error('未找到备份');toast('已恢复原来的壁纸。');}catch(e){toast(e.message);}});
    }));paths.add(restore);

    for(const key of ['library-root','library-revision','static-revision'])watch(key,()=>{library.set_subtitle(settings.get_string('library-root'));reload();});
    for(const key of ['runtime-status','enabled','selected-id','fps'])watch(key,()=>{if(key==='runtime-status'){try{model.connected=JSON.parse(settings.get_string(key)).active===true;}catch(_){}}updateStatus();});
    for(const key of ['rotation-all','rotation-ids'])watch(key,scheduleRotationRebuild);
    for(const key of ['rotation-next-at','rotation-enabled'])watch(key,updateDeadline);
    watch('rotation-mode',()=>{sequence.selected=settings.get_string('rotation-mode')==='shuffle'?1:0;});
    const cancel=new Gio.Cancellable();
    Gio.DBus.session.call('org.gnome.Shell','/org/gnome/Shell/WallpaperManager','org.wallpaper.Manager','Snapshot',null,new GLib.VariantType('(s)'),Gio.DBusCallFlags.NONE,2000,cancel,(bus,result)=>{
        if(model.closed)return;
        try{const [json]=bus.call_finish(result).deep_unpack();model.connected=JSON.parse(json).active===true;}catch(_){model.connected=false;}
        updateStatus();
    });
    window.connect('close-request',()=>{if(busy){toast('正在处理壁纸文件，请稍候');return true;}model.closed=true;if(rotationRebuild)GLib.source_remove(rotationRebuild);rotationRebuild=0;cancel.cancel();for(const id of signals)settings.disconnect(id);signals.length=0;return false;});
    reload();
    // Exposed to the isolated UI driver; no automatic actions or timers.
    return {model,flow,search,filter,apply,mode,importButton,removeButton,capture,runtimeCapture,fps,rotate,interval,sequence,all,rotationList:list,reload,show,pages:[page,rotationPage,options]};
}
