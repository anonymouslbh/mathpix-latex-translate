# Mathpix LaTeX 专业翻译 Skill

将已经通过 Mathpix 导出的英文专业书籍或论文，翻译为专业、一致、可继续修改的简体中文 LaTeX 工程。适用于 Codex 中的长文翻译与续译。

保留现有 Mathpix 流程；输入为原始 PDF、Mathpix 导出的 TeX/ZIP 和图片。这个仓库提供工作流指令与结构检查辅助脚本，翻译、编译和页面核验由 Codex 根据实际材料和环境执行。

## 能做什么

- 按章、节完整翻译正文、标题、图注、表头和脚注，保护公式、编号、引用键及图片路径。
- 维护全书术语表，区分候选译法、用户指定译法和有来源核实的译法。
- 保存输入校验值、翻译进度、排版约定与疑点，支持长书中断后继续。
- 先试译和试排，再展开全书；检查中文字体、文字复制、公式、图表和分页。
- 默认宋体正文、黑体标题、楷体强调，西文 Latin Modern 族、数学 Computer Modern/AMS；跨章共用一个字体配置，实际字体可按用户模板统一覆盖。
- 对照原 PDF 恢复图片的物理尺寸和纵横比，避免 Mathpix 图片被默认放大。
- 按用户要求制作封面和封底，保存生成提示词和资产，接入可重新编译的 TeX 工程，并核对实际 PDF 首末页与正文。

## 安装到 Codex

将本仓库的 GitHub 地址发给 Codex，附上这段要求：

```text
使用 $skill-installer，从我提供的 GitHub 仓库安装 mathpix-latex-translate。
skill 位于仓库根目录，路径为 .，安装名使用 mathpix-latex-translate。
```

也可以把本仓库作为 `mathpix-latex-translate` 文件夹放入当前 Codex 支持的个人 skill 目录或项目的 `.agents/skills/`。目录中应直接包含 `SKILL.md`、`agents/`、`references/`、`assets/` 和 `scripts/`，不要再套一层同名目录。

Codex 会检测新安装的 skill；若列表中未出现，可重启后检查。安装位置和发现机制以 [OpenAI 官方 Skills 文档](https://learn.chatgpt.com/docs/build-skills)为准。

## 使用

在 Codex 中提供原 PDF、Mathpix 导出包及已有术语或模板，例如：

```text
使用 $mathpix-latex-translate，翻译我提供的原始 PDF 和 Mathpix LaTeX 导出包。
目标为简体中文，逐节完整翻译，统一专业术语，保留公式、引用和原图。
先核对材料并试译代表性内容，确定中文排版后继续全书。
交付可编辑的 TeX 工程、编译后的 PDF、术语表和进度记录。
```

继续已有工程时：

```text
使用 $mathpix-latex-translate，读取现有工程的项目记录、术语表和进度，
核对已完成内容后，从第一个未完成单元继续，不重复已验收章节。
```

封面与封底分别指定要求。例如前封上部约 60% 为主题画，中间用协调色横线，下部白底放中英文书名和作者；封底用另一构图的整页纯插画，不放文字。这个版式是可选示例，实际以用户当次要求为准。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `SKILL.md` | skill 入口、核心翻译与验收流程 |
| `agents/openai.yaml` | Codex 展示名称与默认调用提示 |
| `references/project-workflow.md` | 项目记录、续译、结构检查和编译约定 |
| `references/terminology.md` | 全书术语字段、证据与一致性管理 |
| `references/typography.md` | 默认字体、共享配置、跨平台替代与字体验收 |
| `references/cover-workflow.md` | 封面/封底生成、资产记录、TeX 接入和 PDF 核验 |
| `assets/fonts.tex` | 可复制进翻译工程的 XeLaTeX 字体配置片段 |
| `scripts/check_structure.py` | 对照两个 TeX 文件或目录的有限结构清单 |

## 结构检查

脚本只使用 Python 标准库。从仓库根目录运行：

```text
python scripts/check_structure.py /path/to/baseline /path/to/translation
```

它比较标签、常见引用与文献键、图片路径和环境计数，报告重复标签及环境计数不平衡。退出码 `0` 表示这些有限检查通过，`1` 表示发现差异，`2` 表示输入或读取错误。输入目录内应只包含需要对照的 `.tex` 文件；两个参数为文件时，不会自动展开 `input/include`。

该脚本不是 TeX 解析器，不验证公式等价、译文覆盖、术语含义、资源是否存在、实际编译或 PDF 版面。结构检查与编译成功都不能代替源文审校和页面检查。

## 所需材料与环境

- 用户已经导出的 Mathpix TeX/ZIP、图片，以及用于对照的原始 PDF。
- 执行此 skill 的 Codex 环境；无需在本仓库填写 Mathpix 账号或 API 密钥。
- 多文件书籍工程需要已有的 LaTeX 构建环境和可用中文字体；实际采用的引擎、宏包及字体写入项目记录。
- 封面生成使用环境中可调用的图像生成能力；没有该能力时，交付边界按实际情况说明。

仓库包含可复用 skill 与辅助脚本，不包含示例书籍的原 PDF、译文、书图或封面成品。

## 设计参考

工作流参考了以下项目所体现的数学翻译与 LaTeX 结构保护思路：

- [mathtranslations-skill](https://github.com/libinyam/mathtranslations-skill)
- [LaTeXTrans](https://github.com/NiuTrans/LaTeXTrans)

上游项目不是运行依赖。本 skill 的约定及脚本范围以本仓库文件为准。
