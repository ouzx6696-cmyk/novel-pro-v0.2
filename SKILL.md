---
name: novel-pro
description: "novel-pro 中文长篇小说创作 Skill，仅面向当前 runtime_profile: novel-pro-0.2 项目：题材初始化、卷幕章规划、单章 Prompt 与 writer、Fast 草稿、Full 冷读返修、显式 Prompt 审核、完本质检与整卷对齐。识别到旧版本、旧 profile、story.yaml 或缺少迁移状态字段时，不直接兼容或同步，先通过完整项目迁移入口重建新项目、搬运内容并核对报告。"
---

# novel-pro v0.2

发行号：`0.2.1-pro`。当前项目必须使用 `story.md` 的 `skill_version: 5.x` 与 `runtime_profile: novel-pro-0.2`。

这是中文长篇小说创作 Skill。它用卷、幕和章纲保持长线连续性，用幕级 Prompt 创建保持阶段理解，用单章 writer 保留每章的创作注意力，再由 Reader 对真实正文作出文学判断。

## 版本门禁与项目迁移

`novel-pro` 只直接支持当前项目。启动时先读取 `story.md` 的 `runtime_profile` 和 `.agent/status.yaml` 的 `migration` 节点：发现 `story.yaml`、缺少 profile、旧 profile、缺少迁移字段或 `cursor.step: migration.review` 时，停止正常创作，不运行 `sync_runtime.py`，提示作者先完成完整项目迁移。

从当前开发版运行：

```text
python tools/migrate.py <旧项目> <新项目>
```

迁移会在新目录重新初始化当前项目，搬运故事、设定、规划、Prompt、草稿和正文，写入 `.migration/report.md` 与机器可读报告，并列出已完成文件、新版缺失内容文件、未映射旧文件和可清理旧运行时文件。旧项目创建阶段保持不变。作者核对报告后运行 `finalize`，再按报告运行 `cleanup --confirm`；清理不删除正文、规划、设定、任务历史或未映射文件。

## 创作主线

```text
确认题材
→ 初始化骨架
→ 卷纲与本卷必要设定
→ 整卷幕地图与详细幕纲
→ 按幕形成章纲
→ 按幕或连续批次创建单章 Prompt
→ prompts.ready
→ Fast 或 Full
```

初始化只建立项目骨架。新项目从 `outline.volume` 开始，依次完成卷纲、幕纲、章纲和 Prompt。Prompt 全部形成后才进入自动写作。

## 任务粒度

- volume-planner 一次负责一卷。
- act-planner 一次负责整卷幕地图或一个详细幕。
- chapter-planner 一次负责一幕章纲。
- prompt-crafter 一次负责一幕；长幕时一次负责一个连续批次。
- 每章形成一个独立 Prompt 文件。
- writer 一次负责一章。
- Reader 一次顺序阅读一幕。

批量用于减少调度等待，同时保留真实创作范围：Prompt 创建共享幕级理解，writer 保持单章独立上下文，Reader 保持幕级连续阅读。

## 角色地图

| 类别 | 角色 | 任务范围 |
|---|---|---|
| 顶层调度 | `novel-agent` | 阶段调度、writer base、恢复与提交 |
| 规划 | `volume-planner`、`act-planner`、`chapter-planner` | 卷纲、幕纲与章纲 |
| Prompt | `prompt-crafter`、`prompt-reviewer` | Prompt 创建与用户显式要求的审核 |
| 正文 | `writer`、`reader` | 单章创作与整幕冷读复读 |
| 表达 | `anti-ai` | Reader 点名后的普通 Full 表达处理 |
| 完本 | `completion-reviewer`、`completion-editor` | 显式完本阅读与局部 EDIT 候选 |

## Prompt 创建

prompt-crafter 从当前幕纲、任务范围内的章纲、有效承接、人物设定、项目文风、题材和相关创作知识建立完整理解，再顺序写出范围内每章的 `prompts/vol-N-ch-M.md`。

每份 Prompt 把章纲转成人物可以执行的行动过程：目标、筹码、阻力、策略、反制、转折、选择、后果和下一步触发。文风与题材在创建阶段转化为本章的表达材料。

普通幕由一个 prompt-crafter 创建全部 Prompt。长幕按叙事子阶段切成连续批次，每个批次创建多章独立 Prompt。长期目标范围内的 Prompt 全部完成后进入 `prompts.ready`。

## 显式 Prompt 审查

Prompt reviewer 只响应用户明确的审核提示词请求。它先独立阅读目标 Prompt，再读取所在幕纲和对应章纲，形成 `PASS`、`FIX` 或 `STOP` 报告。

Prompt 审查是按需能力，不参与 `prompts.ready` 的形成，也不作为 Fast 或 Full 的默认步骤。

## Writer Base

`templates/runtime/novel-base.md` 是主代理构造 writer 子代理的模板。进入 Fast、Full 首稿或内容返修时，主代理先阅读模板，再结合目标章节、任务模式、Prompt、输出位置和明确的返修焦点写成单章 writer base。

主代理使用这份 base 创建独立 writer，并交付一个目标 Prompt。writer 的完整创作上下文由单章 base 与单章 Prompt 组成。base 建立身份、写作方式和事实边界，Prompt 提供本章故事与表达内容。

## Fast

```text
prompts.ready
→ 主代理为每章构造 writer base
→ 每章创建一个独立 writer
→ drafts/vol-N-ch-M.md
→ drafts.ready
```

Fast 批量生成未经 Reader 文学验收的草稿。顶层仍阅读实际文字，并决定接受、重派 writer 或把对应章节交回 Prompt 创建；Fast 不进入 Full Reader、表达编辑或 `texts/` 提交链，完成于 `drafts.ready`。

## Full

```text
prompts.ready
→ full.write
→ full.review
→ full.repair
→ full.commit
```

`full.write` 使用与 Fast 相同的 writer 创建机制。`full.review` 由 Reader 按幕冷读正文；`full.repair` 按正文证据处理内容和表达问题；候选完成后重新顺序阅读受影响范围；`full.commit` 把接受正文写入 `texts/`。

## 阅读与质量

文件存在、字段齐全、字数、评分、关键词、覆盖率和脚本输出不能代替文学判断。Prompt、正文和返修质量来自角色对人物行动、因果、信息变化、关系压力、情绪推进和真实阅读体验的完整阅读。

脚本服务初始化、当前项目运行时同步、完整项目迁移和文件安全。Reader 首读正文后再追查规划、Prompt 或表达根因。内容问题交新的 writer，表达问题由 Reader 点名后交表达编辑角色。

## 状态与文件

长期 `.agent/status.yaml` 记录：`outline.volume`、`outline.acts`、`outline.chapters`、`prompts.ready`、`draft.write`、`drafts.ready`、`review`、`volume.complete`、`book.complete`；迁移期间使用 `migration.review`，并在 `migration` 节点记录迁移来源、报告、恢复阶段、文件计数和清理状态。

临时 `.agent/order.yaml` 记录当前 operation、phase、卷幕、章节范围、批次、subtasks、attempt、反馈路径和任务状态。
`.agent/tasks/<task-id>/` 保存当前任务的报告、候选与恢复现场；`.agent/run-log.yaml` 只记录重大失败、中断、重写和作者决策。

`outline.acts` 是长期 cursor 阶段；`outline.act-map` 和 `outline.act` 是该阶段内的临时 operation，不属于长期 cursor。显式完本使用 `completion.inspect`、`completion.revise`，整卷产物对齐使用 `alignment`。

- `volumes/`、`acts/`、`chapters/`：已确认规划。
- `prompts/vol-N-ch-M.md`：单章 Prompt。
- `drafts/vol-N-ch-M.md`：未经 Reader 文学验收的草稿。
- `texts/vol-N-ch-M.md`：Reader 接受后的正文。

## 路由

- 卷纲与章纲：`skills/planning.md`
- 幕规划：`skills/act-planning.md`
- Prompt 创建与显式审查：`skills/prompt.md`
- 状态、模式与恢复：`skills/dispatch.md`
- writer base、Fast 与 Full 写作：`skills/writing.md`
- Reader、返修与提交：`skills/review-archive.md`
- anti-AI 与 completion-editor 共用编辑边界：`skills/edit-boundary.md`
- 显式完本任务：`skills/completion-quality.md`
- 显式整卷对齐：`skills/volume-alignment.md`
- 完整项目迁移：`skills/migration.md`

仓库文档使用源码路径 `skills/`、`agents/`、`templates/runtime/`。初始化项目时，运行时资源会改写到 `.claude/skill-resources/` 与 `.claude/agents/`；部署后的 `CLAUDE.md` 使用部署路径。
