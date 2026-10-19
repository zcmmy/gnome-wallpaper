# 多语言音乐信息与文字渲染

## 原因

部分壁纸通过 MPRIS 获取正在播放的音乐标题、艺人或专辑，再由场景脚本更新文字层。
DBus 与 QuickJS 链路使用 UTF-8；原渲染器虽然解码了多字节字符，但只使用一张字体。
壁纸的内嵌字体或原默认 DejaVu Sans 往往不包含中日韩字符。
`FT_Load_Char` 对缺字仍可成功返回 `.notdef` 字形，因此旧的成功检查没有触发字体回退，表现为重复方框或缺字。

## 修复范围

- 保留壁纸字体已有字形，只有缺字才根据 Fontconfig 的字符覆盖、字重和斜体配置查找系统字体。
- 核验 FreeType 实际字形索引，支持 TTC/OTC 字体集合的子字体索引，不把缺字当成正常字形。
- 缓存字符选择和字体文件，复用打开的字体；字号改变时同步所有回退字体。文字与字号未变时仍不重建纹理。
- 测宽、截断和绘制共享字体选择，避免混排时测宽与实际显示不一致；保留超出 advance 的字形边缘。
- UTF-8 解码只接受合法 Unicode 标量，拒绝过长编码、代理码点、截断和越界序列，错误字符后面的有效文字仍保留。
- 字形位图按格式读取，兼容灰度、单色与 BGRA alpha，以及带填充或负方向的行距。
- 所有场景文字层共用该修复，包括音乐信息、普通文本和脚本更新；未改 GNOME 插件、频谱、FPS 或静态图库。

字体回退依赖系统已安装的字体，不能生成字体中不存在的字形。
安装新的字体后，重新开启动态播放以重建字体缓存。新建默认系统字体仍优先 DejaVu Sans，避免改变已有拉丁文字外观。
这是 Unicode 字形覆盖修复，不代表完整支持所有复杂文字整形、双向混排或彩色/组合 emoji。

## 验证

`renderer/tests/check-unicode-text.cpp` 使用独立 Fontconfig 配置与系统提供的 DejaVu Sans、Noto Sans CJK：

- 先确认旧的单字体路径对汉字返回缺字，但 `FT_Load_Char` 返回成功。
- 验证简繁中文、日文假名与汉字、韩文、扩展拉丁、希腊、西里尔及补充平面字符有有效字形与非空像素。
- 验证 TTC、字体缓存、字号变化、原有 ASCII 字形保留、不可用字符及各类无效 UTF-8。
- 验证单色字形位图和负 pitch；同时通过地址/未定义行为检查。

`integration/tests/check-unicode-media.py` 在私有 DBus、独立 XDG 路径和 headless GNOME 中启动合成音乐信息服务：

```bash
python3 integration/tests/check-unicode-media.py \
  --renderer /新构建目录/output/linux-wallpaperengine \
  --baseline /原版本目录/libexec/linux-wallpaperengine \
  --libraries /依赖库目录 \
  --assets /用户自备公共资源目录 \
  --output /尚不存在的测试输出目录
```

测试比较音乐信息经过脚本后的截图与同一段字面文字的截图，并与旧渲染器对照；检查 ASCII 行保持一致。
合成场景不含第三方壁纸、真实音乐信息或用户静态图。测试不会切换真实桌面、播放音乐或修改用户配置。

## 部署

这是 C++ 后端修复，单独安装 GNOME 插件 ZIP 不会更新后端。
构建时新增 Fontconfig 开发依赖，运行时需要 Fontconfig 及目标语言字体。
部署共享库/可执行程序需使用临时文件加原子替换，不得覆盖运行中的 inode；既有播放进程继续使用旧映射，
下一次用户关闭并重新开启动态模式才加载新版本。无需重启 GNOME。

参考：[FreeType 字符映射](https://freetype.org/freetype2/docs/reference/ft2-character_mapping.html)、
[Fontconfig 开发文档](https://fontconfig.pages.freedesktop.org/fontconfig/fontconfig-devel/)。
