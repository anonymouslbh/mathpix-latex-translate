# 项目状态与验证

推荐目录：source/ 保存输入；baseline/ 保存核对过的源文工程；translation/ 保存中文工程；build/ 保存构建输出；qa/ 保存结构报告、审校与版面记录。项目根目录保存 project.json、glossary.tsv、style-guide.md、progress.md、issues.md。已有工程优先沿用布局。

project.json 记录 source_language、target_language、domain、inputs（路径/哈希）、baseline_main、translation_main、build_command、output_pdf；路径相对于项目目录。无法确认领域时从内容推断并记录，可边试译边询问关键歧义。

progress.md 表格按稳定单元 ID 记录：源文件及节标题、源页范围（已核实时）、目标文件、translation/content_review/term_review/build/layout 状态、最后更新时间、下一动作。状态为 pending/in-progress/passed/blocked；记录 blocked 的具体原因。不以译文文件存在自动认定通过。

issues.md 每项记录 ID、源定位、目标定位、类型（OCR/原文疑义/术语/编译/版面）、证据、处理、状态。style-guide.md 保存模板/引擎/字体/尺寸/标点/首次双语和图表处理约定。

字体按 [typography.md](typography.md) 统一：project.json 保存实际 font_profile 和共享配置 SHA256，style-guide.md 写同一角色映射；初始化试排后冻结方案，不让各章自行选择。续改已交付工程时，更新 skill 不等于已更改 PDF；实际字体调整后需重新编译和全页复查。

续译先核对输入及已审文件哈希；源文改变时只将受影响单元及依赖项标记重审。章节完成记录构建日志和审校范围。全书完成需汇总所有单元，不能只审最后一章。

## 结构检查脚本

脚本位于本 skill 实际安装目录下的 `scripts/check_structure.py`，不是翻译项目目录下的脚本。先从已加载的 skill 路径确定安装目录，再运行 `python "<skill安装目录>/scripts/check_structure.py" "<baseline目录或tex>" "<translation目录或tex>"`；工程参数使用实际绝对路径，或相对当前工作目录的正确路径。可将标准输出重定向至工程的 qa/structure.json。仅使用 Python 标准库。

脚本递归扫描提供目录下的 .tex 文件，比较 label、ref/autoref/eqref 等引用、常见 cite 命令、includegraphics 路径及环境数量，并检查重复标签。目录必须只包含该次比较的工程；备份、试译和生成 TeX 应移出扫描目录。两个参数传文件时只比较这两个文件，不自动解析 input/include。

引用键等差异可能是真实损坏，也可能是经记录批准的适配。检查脚本不提供静默豁免；逐项记录原因后审阅。它不完整支持自定义宏、动态路径、注释特殊环境或条件编译，不检查数学等价、完整覆盖、资源存在、术语语义、PDF 版面。结果包含 limitations；无差异仅表示这些有限结构检查通过。

公式保护：翻译前后对数学区域做逐块差异审查，文字型参数可以有翻译差异；任何符号、运算、数值或单位变化需要对照源 PDF 查明。复杂 TeX 应使用可靠解析方式或人工逐块审阅，不声称正则扫描足以保护全部公式。

## 编译与可读性

先确认命令实际存在。多文件工程采用已有构建流程；无现成配置时按所选引擎处理交叉引用与 bibliography，直到引用收敛。检查编译退出码及日志中的缺字、引用和布局问题，再渲染 PDF 检查页面。单文件且没有外部资源时优先内置编辑器/编译器。

试译阶段建立字号、行距、宽表格、长公式、浮动图表和脚注的稳定处理。修复溢出优先调断行、列宽和环境；不要靠全局缩小字体解决所有问题。用户未要求时不新做封面、不强制出版社模板、不改写参考文献条目。
