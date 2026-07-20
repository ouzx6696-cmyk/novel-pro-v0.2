# Writing

Fast 与 Full 共用同一套单章 writer 派发机制。两种模式都从 `prompts.ready` 开始；差别在于草稿完成后是否进入 Reader、返修和提交。

## 构造单章 Writer

主代理在创建每个 writer 子代理前读取 `templates/runtime/novel-base.md`，再根据当前章节写成单章 writer base。

实例化使用当前任务已经确定的信息：

- 章节标识和任务模式。
- 目标 Prompt 路径。
- 草稿或候选输出路径。
- 内容返修时 Reader 已经确认的问题焦点。

单章 base 作为子代理的初始化提示词。目标 Prompt 作为该章的故事与表达输入。两者共同交给一个全新的 writer；每章拥有独立 base、独立 Prompt、独立上下文和独立输出。

base 的职责是建立 writer 身份和创作边界，Prompt 的职责是提供本章内容。主代理在派发时自然组合这两部分，不生成额外 manifest、质量字段或脚本校验。

## Fast

```text
prompts.ready
→ 顶层确定目标范围和 writer 调度批次
→ 为每章构造 writer base
→ 每章创建一个独立 writer
→ drafts/vol-N-ch-M.md
→ 顶层阅读草稿
→ drafts.ready
```

Fast 的批次只安排 writer 并发。已有草稿保留，当前批次只派发尚未完成的章节。

顶层阅读草稿后，根据正文实际表现选择下一步：正文已经完成 Prompt 的场景过程时接受草稿；正文把行动、反制、选择或后果压成提要时，使用同一 Prompt 创建新的 writer；Prompt 本身缺少可展开内容时，把对应章节交回 Prompt 创建阶段。

Fast 完成于 `drafts.ready`。它交付未经 Reader 文学验收的草稿：顶层仍须阅读实际文字，决定接受、重派 writer 或返回 Prompt 创建，但 Fast 不进入 Full Reader、表达编辑和 `texts/` 提交链。

## Full

```text
prompts.ready
→ full.write
→ full.review
→ full.repair
→ full.commit
```

`full.write` 使用与 Fast 相同的单章 writer 创建方式。已经存在的 draft 由顶层实际阅读后决定是否进入 Reader。

`full.review` 由 Reader 按幕顺序冷读正文。Reader 的证据同时指出问题表现和最可能根因，顶层据此选择返修路径：

- Prompt 已经提供完整人物行动和场景因果，但 draft 没有展开时，使用原 Prompt 与 Reader 的具体问题焦点构造新的 writer base。新 writer 从 Prompt 重新创作完整章节。
- Prompt 本身遗漏关键行动、承接或事实边界时，prompt-crafter 在所在幕或连续批次的理解中只修复受影响 Prompt，随后顶层用修复后的 Prompt 创建新 writer。
- 幕纲或章纲无法共同成立时，返回拥有该产物的 planner，尚不创建 writer。
- 表达问题由 Reader 点名后交 anti-AI。

原 draft 和候选保留在 task 中供 Reader 复读比较，不作为内容 writer 的创作输入。候选完成后，Reader 重新顺序阅读受影响范围。

`full.commit` 把 Reader 明确接受的纯正文写入 `texts/`。

## 恢复

order 保存任务模式、章节范围、Prompt、输出和 subtask 状态。中断后，顶层重新读取模板并为未完成章节构造单章 base；已经完成的 draft 和候选保持原状。

单章 base 是可重新构造的派发上下文，不增加长期状态。恢复是否继续某一章节由顶层阅读当前文件和任务现场后决定。
