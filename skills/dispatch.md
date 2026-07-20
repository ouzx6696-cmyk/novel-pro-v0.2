# Dispatch

Dispatch 连接长期创作阶段与当前临时任务。顶层先读取本模块，再按当前 operation 加载一个对应的创作模块；角色只获得完成自身任务所需的上下文。

## 版本门禁

先读取 `story.md` 的 `runtime_profile` 和 `.agent/status.yaml` 的 `migration` 节点。当前项目必须是 `runtime_profile: novel-pro-0.2`，且存在迁移字段。旧 profile、缺失 profile、`story.yaml` 或缺少迁移字段都视为旧项目：停止创作和运行时同步，提示作者使用 `python tools/migrate.py <旧项目> <新项目>` 完整重建迁移项目。迁移目标在 `migration.review` 时只允许阅读报告和处理迁移，不得推进创作阶段。

## 阶段模块

| 当前任务 | operation | 顶层加载 |
|---|---|---|
| 卷纲与本卷设定 | `outline.volume` | `skills/planning.md` |
| 整卷幕地图、详细幕纲 | `outline.act-map`、`outline.act` | `skills/act-planning.md` |
| 一幕章纲 | `outline.chapters` | `skills/planning.md` |
| Prompt 创建、用户要求的 Prompt 审查 | `prompt.create`、`prompt.review` | `skills/prompt.md` |
| Fast、Full 首稿 | `fast.write`、`full.write` | `skills/writing.md` |
| Full 冷读、返修、复读与提交 | `full.review`、`full.repair`、`full.commit` | `skills/review-archive.md` |
| 全书质检或完本返修 | `completion.inspect`、`completion.revise` | `skills/completion-quality.md` |
| 整卷产物对齐 | `alignment` | `skills/volume-alignment.md` |
| 完整项目迁移复核 | `migration.review` | `skills/migration.md` |

顶层使用阶段模块理解任务、构造 subagent 上下文和处理返回结果，不把模块全文复制进角色 packet。subagent 完成自己的范围后返回，只有顶层维护状态、恢复现场和提交路径。

## 创作顺序

```text
确认题材
→ 初始化骨架
→ outline.volume：卷纲与必要设定
→ outline.acts：整卷幕地图与详细幕纲
→ outline.chapters：按幕完成目标写作范围的章纲
→ prompt.create：按幕或连续批次创建目标范围的单章 Prompt
→ prompts.ready：目标写作范围的 Prompt 已全部形成
→ Fast 或 Full
```

初始化只建立项目骨架。目标写作范围通常是一卷，也可以是作者明确指定的连续章节范围。这个范围写入长期 cursor 的 `range`；幕级任务和调度批次不改变它。

## 两层运行态

`.agent/status.yaml` 只记录长期创作位置：

```text
outline.volume
outline.acts
outline.chapters
prompts.ready
draft.write
drafts.ready
review
volume.complete
book.complete
migration.review
```

迁移目标额外使用 `cursor.step: migration.review`，并在 `migration` 节点记录 `state`、`phase`、源项目、源版本、报告路径、恢复阶段、文件计数和 `cleanup`。`finalize` 将状态恢复到 `resume_step`；`cleanup --confirm` 只处理报告列出的旧运行时文件。

`.agent/order.yaml` 记录一个正在执行或等待恢复的临时任务：operation、phase、卷幕、当前连续范围、批次、subtasks、attempt、反馈路径和任务状态。

`scope.chapters` 是当前 order 处理的闭区间。批次 order 的 subtasks 覆盖这个区间内的每一章。Prompt 创建和 writer 调度都可以分成多个连续 batch；batch 只表示临时执行窗口，不产生长期状态。

subtask 使用同一组进度语义：

- `pending`：尚未开始。
- `running`：对应角色正在执行。
- `completed`：产物已经返回并由顶层读过。
- `failed`：本次执行没有形成可用产物。

order 自身使用 `idle`、`running`、`interrupted`、`completed`。`idle` 时 operation 和 phase 留空，不携带一个尚未启动的任务。

## 规划与 Prompt

volume-planner 一次负责一卷；act-planner 负责整卷幕地图或一个详细幕；chapter-planner 一次负责一幕章纲。目标写作范围内的幕纲和章纲形成后，顶层按幕创建 Prompt。

普通幕由一个 prompt-crafter 顺序创建全部单章 Prompt。长幕按连续叙事阶段分批，一个 prompt-crafter 处理一个批次中的多章。当前 batch 完成后，长期 cursor 仍停留在 `outline.chapters`；只有长期 `range` 内每章的 Prompt 都已形成，才进入 `prompts.ready`。

Prompt reviewer 只响应作者明确的审核提示词请求。审查报告属于当前 task，不改变 Prompt 准备链或长期状态。

## Writer 调度

Fast 与 Full 写作时，顶层先加载 `skills/writing.md`，再读取 writer base 模板，为当前章节形成单章 base。一个全新的 writer 获得这份 base 和一个目标 Prompt，写入一个独立输出路径。

多个 writer 可以并行。每章的 subtask 独立更新；顶层读过返回正文后，才把该章标记为 `completed`。Fast 的全部目标草稿完成后进入 `drafts.ready`。Full 随后进入按幕 Reader 冷读、返修、复读和提交。

Fast 或 Full 开始派发 writer 时，长期 cursor 从 `prompts.ready` 进入 `draft.write`。Fast 的目标草稿全部完成后进入 `drafts.ready`；Full 的目标草稿全部形成后进入 `review`，并由 `full.review`、`full.repair` 和 `full.commit` 推进。内容返修需要新 writer 时，顶层从 `review-archive.md` 的根因判断转入 `writing.md` 构造该章 base，完成后回到 Reader 复读。

Full 提交完成当前长期 `range` 后结束临时 order。这个范围覆盖当前卷且正文全部接受时进入 `volume.complete`；作者只选择了卷内部分范围时，接受正文保留为已发生事实，下一次由作者确定新的写作范围，顶层把 cursor 放到该范围最早尚未完成的阶段。所有卷完成后才进入 `book.complete`。

## 恢复

中断时保留 order、task 报告、已经形成的 Prompt、draft 和候选。恢复先读取长期 status、当前 order 和 task 现场，再逐项处理：

- `completed` 的产物由顶层确认仍存在且内容与任务相符；成立时保留。
- `running`、`failed` 或没有对应产物的 subtask 回到 `pending`。
- Prompt 创建继续当前幕或批次的缺失章节。
- writer 调度重新从模板构造待写章节的 base。
- Reader 重新顺序阅读需要判断的完整范围。

长期 cursor 只在整个长期目标范围的阶段产物成立后推进。文件操作用于保护产物；Prompt、正文、返修和接受结论来自角色与顶层对实际内容的阅读。
