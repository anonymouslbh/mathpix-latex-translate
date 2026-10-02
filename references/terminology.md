# 全书术语管理

glossary.tsv 使用 UTF-8、制表符分列。字段为 `id, source, target, domain, context, policy, status, evidence, forbidden_variants, notes`。实际表头用制表符，不用逗号；禁止字段内出现裸制表符或换行。

- id 是稳定键；source/target 是原文/首选译法。
- domain/context 约束含义、定义或专业范围；同词异义分别建条目。
- policy 为 translate / bilingual-first / keep-original。首次双语按全书稳定规则执行，是否每章重新定义由项目确定。
- status 为 candidate / verified / user-approved；verified 需依据，用户明确指定的译法标为 user-approved，不伪造文献支持。
- evidence 写具体书名、章节、标准编号或链接及支持该词义的证据。notes 记录歧义与推理。
- forbidden_variants 用 `|` 分隔实际需要防止的异译；不是把所有同义表达视为错误。

优先级：用户已明确指定且适用于当前语境的术语；适用领域标准；权威教材与专业文献；有依据的模型建议。出现冲突记录并说明含义，专业风险无法消除时保留英文或首次中英并列，不捏造确定结论。

先抽取后核实，自动提取不等于专业认证。每节只引入相关已定术语，同时保留共享定义上下文。自动检索异译只能生成候选位置，逐处判断语境，不全局盲替换。源术语与目标词次数不同不自动判错（中文省略、复数与同义表达可能合法）。

最终复核包括：定义是否正确，首次出现是否解释，缩写是否对应，近义术语是否被错误合并，同词异义是否误统一，以及术语更改后旧译是否清理。
