# {{project_name}} - novel-pro v0.2

题材：{{genre}}。项目入口是 `novel-agent`。当前运行时 profile 是 `novel-pro-0.2`。

`novel-agent` 先读取 dispatch，再按当前 operation 加载一个对应阶段模块。规划、Prompt、写作、阅读和提交规则按需进入上下文，不整套常驻。

这是中文长篇小说创作项目。创作顺序是：

```text
确认题材 → 初始化骨架 → `outline.volume`：卷纲与必要设定
→ 幕纲
→ 章纲
→ 按幕或连续批次创建单章 Prompt
→ prompts.ready
→ Fast 或 Full
```

## 版本门禁与完整项目迁移

启动时先读取 `story.md` 的 `runtime_profile` 和 `.agent/status.yaml` 的 `migration` 节点。发现旧 profile、缺少 profile、`story.yaml`、缺少迁移字段或 `cursor.step: migration.review` 时，停止正常创作和运行时同步，提示作者先从当前开发版运行：

```text
python tools/migrate.py <旧项目> <新项目>
```

迁移会在新目录重新初始化当前项目，搬运对应内容并生成 `.migration/report.md`。作者核对报告后执行 `finalize`，再按报告执行 `cleanup --confirm`。清理只处理报告列出的旧运行时文件，不删除正文、规划、设定、任务历史或未映射文件。

Prompt 创建任务处理一幕或一个连续批次，范围内每章分别写入 `prompts/vol-N-ch-M.md`。长期目标范围内的 Prompt 全部形成后才进入 `prompts.ready`。用户明确要求审核提示词时，顶层才创建 prompt-reviewer。

进入 Fast 或 Full 写作时，顶层读取 `.claude/skill-resources/templates/novel-base.md`，为每章构造 writer base，再创建独立 writer 并交付该章 Prompt。

Fast 批量形成未经 Reader 文学验收的 `drafts/`；顶层仍阅读实际文字，但不进入 Full Reader、表达编辑和 `texts/` 提交链。全部目标完成后进入 `drafts.ready`。

Full 按下面的顺序运行：

```text
full.write → full.review → full.repair → full.commit
```

Reader 按幕冷读正文，返修后重新顺序阅读受影响范围，接受正文写入 `texts/`。

## 显式操作、状态与路径

初始化流程统一理解为：确认题材 → 初始化骨架 → 从 `outline.volume` 开始规划。旧项目必须先完成 `migration.review` → `finalize` 的完整迁移。显式全书质检使用 `completion.inspect`，显式完本返修使用 `completion.revise`，整卷产物对齐使用 `alignment`。

`.agent/status.yaml` 保存长期 cursor 和 `migration` 状态；`.agent/order.yaml` 保存当前 operation、phase、卷幕、范围、批次、subtasks、attempt、反馈路径和任务状态；`.agent/tasks/<task-id>/` 保存报告、候选与恢复现场；`.agent/run-log.yaml` 记录重大失败、中断、重写和作者决策。`outline.acts` 是长期 cursor 阶段，`outline.act-map`、`outline.act` 是其中的临时 operation。

恢复时先读取 status、order、当前 task 与 run-log 中相关记录，再按 operation 加载对应阶段模块。本文件使用部署路径：agent 位于 `.claude/agents/`，skills、knowledge 和 writer base 位于 `.claude/skill-resources/`；Skill 源码仓库中的对应路径分别是 `agents/`、`skills/`、`knowledge/` 和 `templates/runtime/`。

脚本只服务初始化、当前项目同步、完整迁移和文件安全。Prompt、正文和返修质量由角色真实阅读人物行动、因果、信息、关系、情绪和阅读体验后判断。
