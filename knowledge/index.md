# Pro 创作知识索引

知识库只帮助 Agent 做创作判断，不定义流程字段或质量门禁。先判断当前任务，再读取最小的相关入口；不要为了证明“使用过知识”而把术语写进产物。

| 任务 | 入口 | 使用者 |
|---|---|---|
| 连载交付、章节最低交付、钩点与节奏 | `webnovel/index.md` | volume-planner、act-planner、chapter-planner、prompt-crafter；Reader 冷读后按需 |
| 题材定位、读者期待、节奏差异 | `genre/index.md` | volume-planner、act-planner、chapter-planner、prompt-crafter |
| 冲突、钩子、情绪、反转、幕结构 | `plot/index.md` | volume-planner、act-planner、chapter-planner、prompt-crafter |
| 对话、对抗、转场等具体写法 | `scene/index.md` | prompt-crafter；Reader 冷读后按需 |
| 角色决策、人物弧线、反派 | `character/index.md` | volume-planner、act-planner、chapter-planner、prompt-crafter |
| 真实表达问题的按需处理 | `anti-ai/index.md` | 只有 Full Reader 点名后由 anti-AI 编辑加载 |

使用顺序是：识别剧情任务，识别场景主导冲突，读取题材差异，再把知识改写成当前人物与事件的具体动作。writer 不读取本索引，而是执行已经自包含的 Prompt。

预生成知识只提供叙事功能、因果条件和复读方向，不提供可直接套用的剧情菜单、正文样句或坏句字面清单。Prompt 创建/修复者和独立审核者不加载 anti-AI 工作规则；anti-AI 只比对 Reader 点名的实际正文，不把诊断措辞写进候选。

volume-planner、act-planner、chapter-planner 和 prompt-crafter 在角色 frontmatter 中挂载各自索引。Reader 与 completion-reviewer 为保护冷读不预挂知识，只有发现问题后按对应 skill 追查原因。顶层不得把知识正文复制进 subagent 提示，也不得用角色扮演跳过角色文件与索引加载。
