# Act Planning

幕是卷内自然形成的叙事阶段，也是章纲规划和 Full 阅读的基本范围。幕边界由人物、关系、信息和局势的阶段变化决定，不按固定章数切分。

## 整卷幕地图

act-planner 先读取已确认卷纲、本卷必要设定、已接受正文和真正相关的创作知识，建立 `acts/volume-N-acts.md`。

幕地图确定：

- 各幕的阶段顺序和叙事功能。
- 每幕的起点、终点与主要冲突。
- 人物弧线和承诺在各幕的推进位置。
- 相邻幕之间需要传递的状态。

幕数量服从卷内冲突的自然发展。`chapter_roles` 只标记幕内章节功能，不代替详细章纲。

## 单幕规划

顶层按叙事顺序创建 act-planner，一次负责一个 `acts/vol-N-act-K.md`。详细幕纲包含：

- `dramatic_task`：本幕必须完成的阶段变化。
- `start_state`：人物、关系、信息、资源和局势的真实起点。
- `conflict_development`：冲突如何建立、加压、转向并形成结果。
- `character_arcs`、`information`、`emotional_curve` 和 `promises`。
- `setting_constraints`：世界、能力、时间、空间和资源边界。
- `continuity_contract`：事实主体、有效阶段、唯一事件归属和退出交接。
- `chapter_roles`：幕内各章的功能和状态变化。
- `end_state`：下一幕能够直接承接的具体状态。

## 幕间承接

幕规划按叙事顺序检查上一幕终点、当前幕起点和下一幕入口。当前幕拥有自己的修改权；相邻幕的问题返回顶层交给对应 act-planner。

已接受正文提供已经发生的事实。正文终点与后续入口一致时直接推进；真实偏差只调整尚未执行的幕纲、章纲和 Prompt。
