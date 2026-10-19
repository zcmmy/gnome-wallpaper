# 完整插件安装与数据管理

开发中的完整发行包面向 Debian 13 / GNOME 48 / Wayland / x86_64。
它包含场景/视频后端及私有运行库；图形驱动、GNOME 桌面、Python/PyGObject、Fontconfig 配置与字体由系统提供；中文、日文、韩文显示需要对应字体。
安装器预检宿主与后端依赖，不在安装时联网或编译。当前构建不是跨发行版通用二进制。

## 安装

将同次构建的全部附件放在同一目录，先校验：

```bash
sha256sum --check SHA256SUMS
python3 install.py ./gnome-wallpaper-<版本>-linux-x86_64.shell-extension.zip
```

第二行是统一安装入口；不用解压、部署 runtime、编译 schema 或设置后端路径。
更新会结束本扩展的播放/截图，暂存校验后原子交换程序目录并保留旧版。
不会注销、重启 GNOME、自动启用扩展或添加启动项。Shell 已缓存旧模块时，下次登录加载新版。
不要将 ZIP 直接解压覆盖正在使用的插件；当前完整包通过统一安装器进行安全升级。

正常启用扩展后，在设置中导入自己的公共 assets 和壁纸；已有静态图可直接使用静态模式。
只有显式开启动态才启动后端，默认 15 FPS；场景辅助截图仍独立以 4K 渲染并缩小到 1080p。

## 数据与迁移

程序安装在标准 GNOME 扩展目录，用户数据在 `$XDG_DATA_HOME/gnome-wallpaper/`。
未设置 XDG 时数据位于 `~/.local/share/gnome-wallpaper/`，缓存和日志分别位于标准 cache/state 目录。
静态图留在管理图库内，缩略图可重建；更新或卸载程序不删除用户数据。

设置中的“迁移旧版资源”读取旧路径快照，确认复制量后迁移 assets、壁纸及静态图，保留原目录。
同名条目跳过，不覆盖用户图。迁移不启动动态，不重置 FPS 或轮换设置。
导入使用数据盘上的暂存目录、校验、写锁和提交日志；失败/取消清理自身暂存内容。
中断提交可在下一次资源操作时继续完成。新版数据格式不兼容时停止写入。

回滚程序使用安装器返回的备份路径：

```bash
python3 install.py --restore /安装目录的同级备份目录
```

回滚只交换程序，不删除图库、assets 或静态图。普通卸载也只删除程序目录。

## 构建与来源

```bash
make package-backend
make extension DEST=/新的输出目录
```

程序白名单排除用户 assets、壁纸、截图、日志与开发机配置；后端只装入 scene/video 组件，不包含 CEF。
`backend-manifest.json` 列出宿主 ABI、私有库、哈希、来源包、头文件/协议源码输入、构建参数和提交；组包前核对后端构建记录与二进制哈希。
`renderer-corresponding-source.tar.gz` 对应实际后端构建提交；私有 Debian 库的精确源包可由
`fetch-sources.py backend-manifest.json /新的源码目录` 下载，版本不可替换。
公开二进制发布前必须一并提供这些对应源码及构建材料并通过干净环境验收；本轮不自动发布 Release。

构建依赖版本记录在 `packaging/debian13-build.lock.json`。`container-build.sh` 只能在一次性 Debian 容器中运行，版本不可用时失败，不自动换成新版本。容器基础镜像标签本身不保证字节级可复现；最终清单和库哈希才是本次产物身份。

当前验证范围及发布前门槛见 [完整包验证记录](PACKAGING-VALIDATION.md)。
