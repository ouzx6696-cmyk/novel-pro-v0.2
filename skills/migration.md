# 项目迁移

`novel-pro` 不再直接兼容旧版本小说项目。发现 `story.yaml`、缺失 `runtime_profile`、旧 profile，或缺少迁移字段时，停止正常创作和运行时同步，先引导作者完成一次完整项目迁移。

## 迁移入口

从当前开发版技能目录运行：

```text
python tools/migrate.py <旧项目> <新项目>
```

迁移入口会调用当前版初始化流程，在全新的目标目录建立项目骨架、状态机、运行时资源和项目说明，再按文件类别搬运旧项目的故事、设定、规划、Prompt、草稿和正文。旧项目在创建阶段保持只读。

迁移完成后必须先阅读新项目的 `.migration/report.md`。报告至少包含：

- 已完成文件及源、目标映射。
- 对比新版项目所缺失的内容文件。
- 对比新版项目所缺失的项目骨架文件。
- 对比新版项目所缺失的运行时文件。
- 未自动搬运、需要人工判断的旧文件。
- 可以安全清理的旧版本运行时文件。

核对无误后执行：

```text
python tools/migrate.py finalize <新项目>
python tools/migrate.py cleanup <新项目> --confirm
```

`finalize` 才恢复旧项目原本可恢复的创作阶段。`cleanup` 只删除报告列出的旧运行时文件，不删除正文、规划、设定、任务历史或未映射文件；未映射内容必须人工处理。

## 状态机

迁移目标的 `.agent/status.yaml` 使用 `cursor.step: migration.review` 暂停正常创作，并在 `migration` 节点记录源项目、源版本、报告、恢复阶段、文件计数和清理状态。

迁移状态按下面的边界处理：

```text
migration.review
→ 阅读 .migration/report.md
→ migration.state=complete（finalize）
→ migration.cleanup=complete（cleanup --confirm）
→ cursor.step 恢复为 resume_step
```

迁移阶段不得直接写正文、推进规划或调用 `sync_runtime.py`。如果报告存在缺失内容或未映射文件，先交给作者决定如何补齐，再继续创作。
