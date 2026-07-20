# 局部编辑边界

本模块是 anti-AI 与 completion-editor 共用的局部编辑权威边界。两者只处理 Reader 或 completion-reviewer 已经用正文证据点名、边界清楚的局部问题，不自行扩大任务范围。

- 不得新增场景、线索、回忆、心理、环境、设定、伏笔、笑点或字数。
- 不得改变剧情、人物选择、人物动机、POV、信息顺序、人物声线或章末状态。
- 不处理跨章事实、核心因果、场景骨架、Prompt 或规划问题；这些问题返回顶层并进入 `REGENERATE` 或对应上游角色。
- 不做词频、密度、AI 味评分或统一润色。边界无法确认时保留原文，交 Reader 整体复读。

anti-AI 只处理普通 Full 中 Reader 点名的表达问题；completion-editor 只处理显式 `completion.revise` 中被分流为 `EDIT` 的局部表达、可信度、连续性或清晰度问题。两者输出完整候选，不直接提交 `texts/`。
