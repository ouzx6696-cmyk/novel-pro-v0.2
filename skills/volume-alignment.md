# Volume Alignment

整卷对齐只在作者明确要求时运行。它按叙事顺序检查尚未执行的幕纲、章纲和 Prompt 是否共同服务卷目标，并把修改交给拥有对应产物的角色。

## 幕纲

act-planner 按幕检查 `start_state`、`dramatic_task`、冲突发展、人物与信息变化、continuity contract、`chapter_roles` 和 `end_state`。相邻幕接口在同一条卷内因果线上衔接。

## 章纲

chapter-planner 一次处理一幕，顺序复读该幕全部章纲。第一章承接幕起点，最后一章交付幕终点；人物选择、信息取得、能力资源、伏笔和唯一事件在幕内连续。

## Prompt

章纲稳定后，prompt-crafter 以一幕为任务创建全部单章 Prompt。长幕按连续叙事阶段分批，每个批次创建多章独立 Prompt。

对齐任务形成或修复 Prompt，不自动创建 prompt-reviewer。作者明确要求审核提示词时，顶层另行创建 `prompt.review` 任务。

## 正文之后

已接受正文提供已经发生的事实。正文终点与下一幕入口一致时继续创作；真实偏差只影响尚未执行的幕纲、章纲和 Prompt。

对齐使用当前 order 与 task 保存范围和报告，不增加长期创作节点。
