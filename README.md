# novel-pro v0.2 (`0.2.2-pro`)

novel-pro 中文长篇小说创作 Skill，是可独立运行的文学内核。当前项目必须使用 `runtime_profile: novel-pro-0.2`。项目从题材和卷纲开始，用幕与章纲组织长线内容，用幕级任务创建单章 Prompt，再由主代理为每章构造 writer base 并派发独立 writer。

## 版本门禁与完整迁移

旧 profile、缺少 `runtime_profile`、`story.yaml` 或缺少/不完整 `.agent/status.yaml` 的 `migration` 节点都视为旧项目。novel-pro 不直接兼容旧项目，也不允许旧项目继续走运行时同步；先从当前开发版运行：

```text
python tools/migrate.py <旧项目> <新项目>
```

迁移入口会重新初始化新项目、搬运对应内容、生成差异报告。核对 `.migration/report.md` 后执行 `finalize`，再按报告执行 `cleanup --confirm`。源项目在报告核对前保持不变。

## Novel Desk 与 TASKS.md 协作

Novel Desk 是可选的本地作者工作台，不是 Agent 控制台：它不启动 Runtime、不连接 MCP、不调度 Agent。`novel-pro` 可完全脱离 Desk 运行；使用 Desk 时，双方只通过同一个项目文件夹协作。

项目根目录 `TASKS.md` 是唯一的作者到 Agent 外壳交接文件。收到“处理任务清单”后，Agent 必须先读取所有 `pending` 项，核对来源路径、内容 hash 和可选 anchor，汇总拟处理范围与既有 Skill 路径，并等待作者明确确认。确认后才更新任务为 `in_progress`，按原有文学流程执行，最后回写 `completed` 或 `blocked`、结果说明和产物路径。

`TASKS.md` 不替代 `.agent/status.yaml`、`.agent/order.yaml` 或 `.agent/tasks/`；它也不改变角色、状态机、正式正文提交和完整迁移。`texts/` 继续只通过原有 Reader 接受与 `full.commit` 边界写入。完整迁移不自动搬运 `TASKS.md`：旧项目保留历史，新项目首次创建 Desk 任务时再生成清单。

## 主线

```text
确认题材 → 初始化骨架
→ `outline.volume`：卷纲与必要设定
→ 幕纲
→ 章纲
→ 按幕或批次创建单章 Prompt
→ prompts.ready
→ Fast 或 Full
```

Prompt 创建任务处理一幕或一个连续批次，最终仍是一章一个 `prompts/vol-N-ch-M.md`。Prompt reviewer 只在用户明确要求审核提示词时启动。

## Writer 派发

`templates/runtime/novel-base.md` 是主代理使用的 writer base 模板。主代理为每章生成单章 base，再创建 writer，并把该章 Prompt 交给它。

```text
novel-base template
→ chapter writer base
→ one writer + one Prompt
→ one draft
```

base 定义 writer 身份、写作方式和事实边界；Prompt 提供本章剧情、承接、文风、题材与收束。

## Fast

Fast 从 `prompts.ready` 开始，为目标范围内每章创建独立 writer，输出未经 Reader 文学验收的草稿到 `drafts/`。顶层仍阅读实际文字并决定接受、重派或返回 Prompt 创建；Fast 不进入 Full Reader、表达编辑和 `texts/` 提交链。全部完成后进入 `drafts.ready`。

## Full

Full 同样从 `prompts.ready` 开始：

```text
full.write → full.review → full.repair → full.commit
```

Reader 按幕冷读正文，内容问题交新的 writer，表达问题由 Reader 点名后处理，接受正文写入 `texts/`。

## 运行态

- `.agent/status.yaml`：长期创作阶段和迁移状态。
- `.agent/order.yaml`：当前任务、范围、批次与 subtasks。
- `.agent/tasks/<task-id>/`：报告、候选和恢复现场。
- `.agent/run-log.yaml`：重大失败、中断、重写和作者决策。

新项目初始化后的 cursor 为 `outline.volume`。初始化只创建骨架，卷纲和必要设定由 volume-planner 与作者共同形成。

## 初始化

```text
python tools/init.py <project-path> --genre <题材编号>
```

初始化接受不存在的目录或空目录，并部署项目骨架与运行时资源。

## 角色

| 角色 | 任务范围 |
|---|---|
| `novel-agent` | 顶层阶段调度、writer base 构造、恢复与提交 |
| `volume-planner` | 一卷卷纲与必要设定 |
| `act-planner` | 整卷幕地图或一个详细幕 |
| `chapter-planner` | 一幕全部章纲 |
| `prompt-crafter` | 一幕或一个连续批次的多章 Prompt |
| `prompt-reviewer` | 用户显式要求的 Prompt 审查 |
| `writer` | 一章草稿或内容返修 |
| `reader` | 一幕冷读与复读 |
| `anti-ai` | Reader 点名后的表达处理 |
| `completion-reviewer` | 显式完本阅读 |
| `completion-editor` | 显式完本任务中的局部编辑 |

脚本只处理初始化、当前项目同步、完整迁移和文件安全。小说质量由创作角色与 Reader 对实际文字的阅读决定。

## 操作与路径

初始化流程统一理解为：确认题材 → 初始化骨架 → 从 `outline.volume` 开始规划。`outline.acts` 是长期创作阶段；`outline.act-map`、`outline.act` 是该阶段中的临时 operation。显式能力还包括全书质检 `completion.inspect`、完本返修 `completion.revise` 和整卷产物对齐 `alignment`。

仓库说明使用源码路径 `skills/`、`agents/`、`templates/runtime/`。初始化后，这些资源分别部署到项目的 `.claude/skill-resources/` 和 `.claude/agents/`，因此项目内 `CLAUDE.md` 使用部署路径。`tests/` 是源码仓库的开发验证资产，不进入 `skill.json` 的发行文件清单。
