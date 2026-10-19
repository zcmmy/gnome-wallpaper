# Git 与版本发布

统一仓库：git@github.com:zcmmy/gnome-wallpaper.git
稳定分支：main；日常开发分支：dev。当前源码版本：VERSION 中的 v0.0.3；GitHub Release 保持 v0.0.2。
本次仅推送 dev/main，v0.0.3 附注标签保留在本地；推送 v* 标签会触发 Release 工作流，因此未经发布授权不要推送该标签。
未发布功能先进入 dev，达到发布条件并完成审查后再合并到 main；普通功能提交不代表新版本发布。
renderer/source、gnome/extension 均是顶层仓库中的普通源码目录，不是 gitlink/submodule。
选择完整源码快照是为了让本地补丁可随一次 clone 获得，避免引用只有开发机才有的提交。
不自动推送回上游项目，不依赖原始嵌套 .git。

## 常规开发

日常修改在 dev 上进行；需要独立功能分支时，从 dev 创建。

```text
git switch dev
git pull --ff-only
git switch -c feature/主题
git status --short
make check
git add <明确的源码/文档路径>
git diff --cached --stat
git commit
git push -u origin HEAD
```

功能分支完成后先合并到 dev。准备发布时审查 dev 的完整变更，更新 VERSION、[CHANGELOG.md](../CHANGELOG.md)，
再将确认发布的内容合并到 main 并创建新的附注标签。
v0 是已发布基线，不重写或强制移动该标签；修正发布时创建新版本。
无需为了普通项目修改而修改 third_party/sources.lock.json 中的上游 commit。

## 更新上游

## 1. 在临时目录克隆 sources.lock.json 指定的上游，检出当前锁定 commit 和拟更新 commit。

## 2. 对照本地已修改的源码，以三方合并/逐项移植方式处理，保留本项目接口和测试。

## 3. 保留 External 子目录的许可证，更新锁定 commit/tree、来源和改动索引。

## 4. 运行两层单元测试及隔离 GNOME 集成；验证后单独提交依赖升级。

不要直接覆盖 renderer/source 或 gnome/extension，也不要直接运行上游混合安装脚本。

## 发布内容

跟踪源码、脚本、测试、文档、依赖来源及上游许可证；不跟踪用户壁纸和 WE assets。
.gitignore 排除 build、deps、运行会话、个人报告/备份、日志和编译 schema。
reports/backups/runtime 各保留一份目录说明。私有资源测试需用户自备素材，详见 [VERIFICATION.md](VERIFICATION.md)。

## 本机迁移备份

原来两个嵌套仓库的完整 Git 数据、工作区 diff、文件清单已保存在 backups/git-v0-*。
本机 .git/upstream-backup-location 记录准确位置，不上传远端。
还原旧仓库时应使用独立目录检出备份并应用当时 diff；不要在当前统一仓库内重新放入嵌套 .git。

## 插件 Release 发布

更新 VERSION、CHANGELOG、README、版本说明、PLUGIN-INSTALL 和 metadata 整数版本后运行 `make check`。
`make release-package` 生成 `build/releases/<版本>/`，该目录须尚不存在，避免混入旧产物。
附件为插件 ZIP、原子安装器、Markdown 安装说明和 SHA256SUMS，不包含用户资源或 C++ 后端。
ZIP 条目固定时间与权限，同一 GLib/Python 工具链下可重复构建；不同版本 schema 编译工具可能产生不同结果。

完成 dev → main 合并并创建附注标签后，推送 main、dev 和新标签。
`.github/workflows/release.yml` 在版本标签上校验 VERSION、构建插件、验证校验和，先建立草稿并上传完整附件，再公开 Release。
工作流只为发布任务授予仓库 contents:write 权限，使用 GitHub 自动生成的短期 token。
失败重试只允许更新同名草稿，不覆盖已公开 Release；历史标签不移动。
发布后核对远端分支、标签、Release 附件，并下载验证 SHA-256。
