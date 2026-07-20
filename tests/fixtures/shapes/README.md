# v0.2 形态夹具

这些夹具只描述调度输入、输出和恢复形态，不评价小说质量。

| 文件 | 用途 |
|---|---|
| `order.fast.write.example.yaml` | Fast 使用单章 base 与单章 Prompt 生成 draft |
| `order.fast.interrupted.example.yaml` | Fast 中断后保留已有 draft、只恢复缺章 |
| `prompt.batch.example.yaml` | 一个长幕批次任务创建多个单章 Prompt |
| `order.full.review.example.yaml` | Full 按幕 Reader 冷读 |
| `order.full.repair.example.yaml` | 内容问题、表达问题的返修分流 |
| `order.full.commit.example.yaml` | Reader 复读接受后写入 texts |
| `order.completion.inspect.example.yaml` | 显式完本任务复用 order |
| `prompt.chapter.example.md` | 自包含章节 Prompt |
| `reader.report.example.md` | Reader 真实证据报告 |
| `act.continuity.example.md` | 幕间连续性契约 |
| `candidate.bad.mixed.example.md` | 候选混入说明文本的反例 |
| `candidate.good.example.md` | 纯小说正文候选 |

所有 order 示例使用同一组 subtask 状态：`pending`、`running`、`completed`、`failed`。批次的 `scope.chapters` 与 subtasks 一一对应。

对照 `skills/dispatch.md`、`skills/review-archive.md`、`skills/prompt.md` 和 `skills/completion-quality.md` 做人工验收。
