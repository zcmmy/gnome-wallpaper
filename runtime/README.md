# 开发会话与测试环境（不同于 ../wallpaper-runtime 正式运行包）

必须保留：live-extension/、live-desktop/、hq-live/、static-overview-live、runtime-capture-live/。
这些模块被当前 GNOME 会话或 Looking Glass 迁移入口引用，不能当作普通缓存删除。
根下 config/、cache/、state/ 保留给旧桌面试运行工具使用。

可重新生成：capture-test/、manager-test/、manager-ui-test/、manager-hot-test/、
static-background-test/、static-overview-test/、nested/。
通过 make clean-tests 预览；make clean-tests-apply 在核查没有运行引用后清理。
相应 staging / integration 脚本会重新创建目录，不需要手工恢复。
