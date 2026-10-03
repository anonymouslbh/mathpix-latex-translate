# 统一字体

新建中文翻译工程默认使用同一字体方案，优先级为用户明确指定的字体或必须遵守的模板、已记录且经用户接受的项目方案、此默认方案。续改已有工程时先确认实际字体；这份 skill 的更新不自动改写已交付 PDF。

## 默认角色

| 内容 | Windows 默认 | 其他环境的整套备用候选 |
| --- | --- | --- |
| 中文正文、图注、脚注、目录正文 | 宋体 SimSun | FandolSong |
| 中文章节标题、表头和标题型文字 | 黑体 SimHei | FandolHei |
| 中文强调、引文中需要的楷体 | 楷体 KaiTi | FandolKai |
| 西文正文、数字、正文中的英文名 | Latin Modern Roman | 同左 |
| 西文无衬线文字、标题中选择的无衬线部分 | Latin Modern Sans | 同左 |
| 西文代码、等宽文字 | Latin Modern Mono | 同左 |
| 数学公式 | Computer Modern 与 AMS 数学字体 | 同左 |

这是一套按语义角色统一的字体，不把中文、英文、公式全部强制塞进同一字体。默认新书正文 11pt、行距倍率 1.15；图注和脚注沿用同一正文族并通过共享样式缩小字号。标题尺寸按文档层级统一设置，用户模板可覆盖这些默认值。

Windows 字体齐备时试排整套宋/黑/楷方案；缺少其中之一时，整套已安装的 Fandol 字体可作为候选，不能每章自行选择字体。自动选择只用于初始化：通过字形、数学与中文复制检查后，保存实际方案，冻结 `windows` 或 `fandol`，再展开全书。Windows 与 Fandol 的字形并不完全相同；若要不同机器输出同一字形，应在这些机器上固定同一套验证过的可用字体，例如固定 Fandol，不保持 `auto`。

不在 skill 仓库中分发字体二进制文件，也不自动安装字体或 TeX 发行版。找不到所选字体时说明缺失项，保留源工程与未验证状态；不要悄悄换成另一个字体再宣称统一。

## 集中配置

从本 skill 实际安装目录复制 [assets/fonts.tex](../assets/fonts.tex) 到工程的 `translation/fonts.tex`，由唯一入口或共享导言区加载一次。它是 XeLaTeX 字体配置片段，适用于已有 `article`+xeCJK 或 ctex 工程，不是完整书籍模板。

新建 ctex 工程的导言区示例：

```tex
\PassOptionsToPackage{no-math}{fontspec}
\documentclass[UTF8,11pt,fontset=none]{ctexart}
\usepackage{amsmath,amsfonts,amssymb}
\newcommand{\MLTFontProfile}{windows} % 试排后冻结实际方案
\input{fonts.tex}
\linespread{1.15}
\ctexset{
  section/format={\Large\sffamily\heiti\bfseries},
  subsection/format={\large\sffamily\heiti\bfseries},
  subsubsection/format={\normalsize\sffamily\heiti\bfseries}
}
```

上例为导言区片段，不应另建重复主文档。现有 `article` 工程可保留文档类，确保 `no-math` 在 fontspec 首次加载前声明，并在共享标题格式中选择 `\sffamily\heiti`。章节文件只写语义命令，不再写 `\setmainfont`、`\setCJKmainfont`、独立字体回退链或重复字号设置。清理 Mathpix 导言区中冲突的字体选择仅限可编辑基线与译文，原始导出不改写。

`fonts.tex` 不重设页面尺寸、图片尺寸、编号、译文或全部数学符号。默认数学方案以经典 Computer Modern/AMS 为基础，`no-math` 避免西文字体设置意外替换数学字母；粗体数学罗马字母固定为 OT1/cmr。不要为了匹配正文字体而自动引入 unicode-math 或全局替换特殊数学字体。源文必要的特殊符号/数学宏包经兼容性检查后保留，并将实际数学字体及例外记录在方案中。

把 `font_profile` 记录到 `project.json`，字段可适配现有工程：方案 ID、引擎、各文字角色的实际字体名、共享配置路径及 SHA256、字号、行距、特殊数学字体、覆盖理由和验证状态。在 `style-guide.md` 写同一约定。不要只写“宋体风格”而不写真正使用的字体名。

## 封面和原图

要求封面字体与正文方案严格一致时，图像生成只制作主题画；中文书名及作者文字用统一字体在 TeX 或确定性的排版工具中叠加，西文书名使用 Latin Modern Roman 或经用户指定的同一字体族。记录封面字重和字号，而非让生成器自行决定。纯画封底保持无文字。

用户若明确要求整张封面由图像工具生成，遵循该要求并核对字形；生成提示词中的“宋体”不能证明位图使用了精确 SimSun 字体，记录为视觉近似，不声称严格同字体。已有位图封面不因本默认规则自动重做。

原书图片内部字体属于原图内容，保留原图；译文图注、表头、脚注与正文按统一方案排版。字体更新不授权重画实验图或改动数据。

## 试排和验收

试排覆盖中文正文/粗体/楷体、西文常规/粗体/斜体、三级标题、中文图注与脚注，以及希腊字母、粗体向量、分式、上下标、积分与 AMS 符号。检查实际日志、页面字形和 PDF 字体清单，并抽取中文文字核对复制；没有缺字警告也不能证明字体族一致。PDF 子集字体的不同前缀和光学字号允许不同，应按真实字体族及其正/粗/斜体归并核对。

字体文件存在、编译退出码为 0，均不保证中文可复制。例如 Fandol 的 CID 字体需要当前 PDF 输出与提取环境提供有效 Unicode 映射；检查 `/ToUnicode`、字体的 CID 信息及真实提取结果，出现 `Missing language pack for Adobe-GB1`、乱码或中文遗漏时判定未通过。先在现有环境中查明映射问题；无法修复时保留未验证状态，或整套选择另一已验证且可用的字体并记录原因，不能将仅视觉正常的备用方案用于最终交付。

整书完成时检查所有章节与共享入口的字体声明及 PDF 字体清单，记录额外字体来源。已完成工程改变字体会改变行长、分页和目录，因此需要重新编译至引用收敛并复查全部页面；旧版检查记录不能直接沿用。

命令语义参考：[fontspec 手册](https://mirrors.ctan.org/macros/unicodetex/latex/fontspec/fontspec.pdf)、[xeCJK 手册](https://tug.ctan.org/macros/xetex/latex/xecjk/xeCJK.pdf)。实际可用字体和验证结果以当前工程的构建环境为准。
