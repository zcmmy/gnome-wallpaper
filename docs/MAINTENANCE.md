# 目录维护与数据所有权

源码：renderer/source 和 gnome/extension 统一由顶层 Git 跟踪；原嵌套 Git 历史备份在 backups/git-v0-*。
真实运行数据：../wallpaper-runtime/wallpapers，以当前 GSettings library-root 为准。
开发资源：wallpapers、assets；运行包会复制，不靠软链接回指源码。
旧单壁纸 wallpaper/ 仍用于预览和历史测试，不能因为与图库重复就直接删除。
构建：build/portghost 中包含可复用缓存及下载依赖；普通整理不清除此目录。
兼容：sources/ 和 tools/ 仍被构建缓存或旧手动命令引用，保留。
会话：runtime/live-extension、live-desktop、hq-live、static-overview-live 以及根下 config/cache/state 保留。
报告与备份：保留原路径，便于历史聊天链接与回滚；不将报告目录视为缓存一并清除。

## 维护命令

```text
make inventory             统计目录大小、顶层 Git 状态和固定上游来源
make clean-tests           输出白名单测试目录/Python 缓存的清理计划，不删除
make clean-tests-apply     核查同用户进程命令、环境及 cwd 后清理
```

清理器不跟随软链接；检测到挂载点、运行中引用或无法检查同用户进程时拒绝执行。
固定命令的 systemd --user、sd-pam、ssh-agent -D 属于登录基础服务，不作为壁纸测试进程检查。
清理记录保存到 reports/maintenance/；默认不触碰源码、资源、build、deps、备份和当前会话副本。

## 备份

[backups/README.md](../backups/README.md) 给出最近修复对应目录。备份含程序、图片、插件或当时的 dconf，按目录内容恢复。
恢复共享库/程序/图片用临时文件 + 原子重命名；恢复插件用原子目录安装器。
不要直接用历史配置 dump 覆盖当前配置，避免回退不相关的顶栏、Dock 或主题设置。

## 本次整理范围

更新过时的辅助截图说明；统一根目录命令入口和运行包文档模板。
消除管理 UI 测试依赖上一次生成的 manager-test/run-test.sh 的隐式依赖。
只清理停用的测试副本及 Python 字节码缓存，不改变已部署播放逻辑或桌面设置。
