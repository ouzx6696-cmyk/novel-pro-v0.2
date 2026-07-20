# novel-pro 手工流程验收

手工验收通过真实阅读确认创作链是否成立。文件数量、字段覆盖、字数、关键词和脚本结果只用于文件安全，不代表文学质量。

## 版本门禁与完整迁移

- [ ] 旧 profile、`story.yaml`、缺少 profile 或缺少 `migration` 字段时，停止正常创作。
- [ ] 从开发版运行 `tools/migrate.py <旧项目> <新项目>`，不在旧项目原地同步。
- [ ] 新项目进入 `cursor.step: migration.review`，并生成 `.migration/report.md`。
- [ ] 报告列出已完成文件、新版缺失内容文件、未映射文件和可清理旧运行时文件。
- [ ] 核对报告后先执行 `finalize`，再显式执行 `cleanup --confirm`。
- [ ] 清理不删除正文、规划、设定、任务历史或未映射文件。

## 题材与初始化

- [ ] 创建项目前先确定题材。
- [ ] 初始化只形成项目骨架、题材入口和运行状态。
- [ ] 新项目 cursor 位于 `outline.volume`，order 为 `status: idle`。
- [ ] 初始化不生成卷纲、幕纲、章纲、Prompt 或正文。

## 卷、幕与章纲

- [ ] volume-planner 一次负责一卷，形成卷纲和本卷必要设定。
- [ ] act-planner 先建立整卷幕地图，再一次完成一个详细幕。
- [ ] chapter-planner 一次处理一幕，顺序形成并复读该幕全部章纲。
- [ ] 当前幕第一章承接 `start_state`，最后一章交付 `end_state`。

## Prompt 创建

- [ ] 普通幕由一个 prompt-crafter 顺序创建该幕全部单章 Prompt。
- [ ] 长幕按连续叙事阶段分批，一个 prompt-crafter 处理一个批次中的多章。
- [ ] 每章分别形成 `prompts/vol-N-ch-M.md`，没有共享 Prompt。
- [ ] prompt-crafter 阅读项目文风与题材，并把本章有效的表达材料写入 Prompt。
- [ ] 单个幕或 batch 完成后继续下一段，长期目标范围内全部 Prompt 创建完成后进入 `prompts.ready`。

## 显式 Prompt 审查

- [ ] 没有用户审核请求时不创建 prompt-reviewer。
- [ ] 用户明确要求后，reviewer 先单独阅读目标 Prompt。
- [ ] 第二次阅读只使用所在幕纲和对应章纲。
- [ ] 审查报告进入当前 task，不增加长期状态。

## Writer Base 与 Fast

- [ ] 主代理在每次派发 writer 前读取 `novel-base` 模板。
- [ ] 主代理根据章节、模式、Prompt 和输出位置构造单章 writer base。
- [ ] 每个 writer 获得自己的单章 base 和一个目标 Prompt。
- [ ] 多章可以并行，但每章拥有独立 base、writer 和输出。
- [ ] 顶层阅读草稿并决定接受、重派或返回 Prompt 创建。
- [ ] Fast 完成于 `drafts.ready`，不进入 Reader 和 `texts/`。

## Full

- [ ] Full 从 `prompts.ready` 进入 `full.write`。
- [ ] Reader 一次顺序冷读一幕，先形成阅读体验再追查根因。
- [ ] 正文执行失败使用原 Prompt 交新 writer；Prompt 设计不足先修复受影响 Prompt；规划冲突返回对应 planner。
- [ ] 表达问题只有 Reader 点名后才交 anti-AI。
- [ ] 返修后重新顺序阅读受影响范围。
- [ ] 接受正文由顶层写入 `texts/`。
- [ ] 整卷范围全部接受后进入 `volume.complete`，部分范围完成后由下一次目标范围决定最早未完成阶段。

## 恢复

- [ ] order 记录当前范围、批次和章节进度。
- [ ] 当前 batch 的 `scope.chapters` 与逐章 subtasks 完整对应。
- [ ] subtask 只使用 `pending`、`running`、`completed`、`failed`。
- [ ] 中断后保留已经形成的 Prompt、draft 和候选。
- [ ] Prompt 创建继续当前幕或批次的缺失产物。
- [ ] writer 恢复时由主代理重新从模板构造单章 base。
- [ ] 长期 cursor 只在阶段产物真正完成时推进。
