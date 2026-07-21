#!/usr/bin/env python3
"""Static checks for the v0.2 scheduling and runtime contract."""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from runtime_manifest import (  # noqa: E402
    AGENT_FILES,
    PROJECT_TOOL_FILES,
    SKILL_FILES,
    TEMPLATE_FILES,
    runtime_entries,
)


def read(path):
    return Path(path).read_text(encoding="utf-8")


def frontmatter_paths(path):
    parts = read(path).split("---", 2)
    assert len(parts) == 3, path
    return [value.strip().strip("\"'") for value in re.findall(
        r"^\s*-\s*path:\s*(.+)$", parts[1], re.M
    )]


def main():
    manifest = json.loads(read(ROOT / "skill.json"))
    assert manifest["name"] == "novel-pro"
    assert manifest["version"] == "0.2.2-pro"
    assert manifest["license"] == "MIT"
    assert "skill.json" in manifest["files"]
    assert "LICENSE" in manifest["files"]
    assert read(ROOT / "LICENSE").startswith("MIT License")
    for rel in manifest["files"]:
        assert (ROOT / rel.rstrip("/")).exists(), rel

    assert sorted(path.name for path in (ROOT / "agents").glob("*.md")) == sorted(AGENT_FILES)
    assert sorted(path.name for path in (ROOT / "skills").glob("*.md")) == sorted(SKILL_FILES)
    assert TEMPLATE_FILES == ["novel-base.md"]
    assert (ROOT / "templates/runtime/novel-base.md").is_file()
    assert not (ROOT / "agents/novel-base.md").exists()
    assert "runtime_manifest.py" in PROJECT_TOOL_FILES
    assert "migrate.py" in PROJECT_TOOL_FILES
    assert "sync_runtime.py" in PROJECT_TOOL_FILES

    entries = list(runtime_entries(ROOT))
    targets = [target.as_posix() for _source, target, _kind in entries]
    assert len(targets) == len(set(targets))
    for source, target, _kind in entries:
        assert source.is_file(), source
        assert target.parts[0] in {".claude", "tools"}, target

    for agent in (ROOT / "agents").glob("*.md"):
        for rel in frontmatter_paths(agent):
            source = ROOT / "templates" / rel if rel.startswith(".agent/") else ROOT / rel
            assert source.is_file(), f"{agent.name}: {rel}"

    release = manifest["version"]
    assert release in read(ROOT / "SKILL.md")
    assert release in read(ROOT / "README.md")
    assert "runtime_profile: novel-pro-0.2" in read(ROOT / "templates/story.md")
    assert "runtime_profile: novel-pro-0.2" in read(ROOT / "templates/CLAUDE.md") or "novel-pro v0.2" in read(ROOT / "templates/CLAUDE.md")
    assert "step: outline.volume" in read(ROOT / "templates/.agent/status.yaml")
    status_template = read(ROOT / "templates/.agent/status.yaml")
    assert "migration:" in status_template
    for field in (
        "state",
        "phase",
        "source_project",
        "source_version",
        "target_project",
        "report_path",
        "resume_step",
        "cleanup",
        "completed_count",
        "missing_count",
        "unmapped_count",
    ):
        assert f"  {field}:" in status_template
    assert "[1, 80]" not in read(ROOT / "templates/story.md")

    status = read(ROOT / "templates/.agent/status.yaml")
    order = read(ROOT / "templates/.agent/order.yaml")
    for marker in ("task_id:", "operation:", "phase:", "scope:", "batch:", "subtasks:", "feedback_path:", "status:"):
        assert marker in order
    assert "step:" not in order

    genre_index = read(ROOT / "knowledge/genre/index.md")
    registered = set(re.findall(r"(?m)^\| `([^`]+)` \|", genre_index))
    genre_files = {
        path.stem for path in (ROOT / "knowledge/genre").glob("*.md") if path.name != "index.md"
    }
    anti_ai_files = {path.stem for path in (ROOT / "knowledge/anti-ai/genre").glob("*.md")}
    assert registered == genre_files == anti_ai_files

    for index in (ROOT / "knowledge").rglob("index.md"):
        for rel in re.findall(r"`([^`<>]+\.md)`", read(index)):
            if rel.startswith(("vol-", "volume-", "settings/", ".agent/")):
                continue
            target = ROOT / rel if rel.startswith("knowledge/") else index.parent / rel
            assert target.is_file(), f"{index.relative_to(ROOT)}: {rel}"

    skill = read(ROOT / "SKILL.md")
    readme = read(ROOT / "README.md")
    dispatch = read(ROOT / "skills/dispatch.md")
    migration = read(ROOT / "skills/migration.md")
    writing = read(ROOT / "skills/writing.md")
    review = read(ROOT / "skills/review-archive.md")
    prompt = read(ROOT / "skills/prompt.md")
    prompt_batch = read(ROOT / "tests/fixtures/shapes/prompt.batch.example.yaml")
    interrupted_fast = read(ROOT / "tests/fixtures/shapes/order.fast.interrupted.example.yaml")
    prompt_agent = read(ROOT / "agents/prompt-crafter.md")
    prompt_reviewer = read(ROOT / "agents/prompt-reviewer.md")
    anti_ai_agent = read(ROOT / "agents/anti-ai.md")
    writer = read(ROOT / "agents/writer.md")
    reader = read(ROOT / "agents/reader.md")
    completion = read(ROOT / "skills/completion-quality.md")

    # Novel Desk is an optional local shell. The author-to-Agent handoff must
    # remain outside the literary state machine and require explicit consent.
    for marker in ("Novel Desk", "TASKS.md", "等待作者", "不替代 `.agent/status.yaml`"):
        assert marker in skill + readme, marker

    assert "skills/completion-quality.md" not in frontmatter_paths(ROOT / "agents/novel-agent.md")
    assert "skills/completion-quality.md" not in frontmatter_paths(ROOT / "agents/act-planner.md")
    assert "skills/completion-quality.md" not in frontmatter_paths(ROOT / "agents/chapter-planner.md")
    assert "skills/completion-quality.md" not in frontmatter_paths(ROOT / "agents/prompt-crafter.md")
    assert frontmatter_paths(ROOT / "agents/completion-editor.md") == [
        "skills/completion-quality.md",
        "skills/edit-boundary.md",
    ]

    for marker in ("Fast", "Full", "drafts/", "texts/", "prompts.ready", "full.review", "full.commit", "migration.review", "tools/migrate.py"):
        assert marker in skill + dispatch
    assert "migration.state=complete" in migration
    assert "migration.cleanup=complete" in migration
    assert "cleanup.complete" not in migration
    for marker in ("outline.volume", "volume-planner", "卷纲"):
        assert marker in skill + dispatch + read(ROOT / "agents/novel-agent.md")
    for marker in ("prompt.create", "prompt.review", "fast.write", "full.write", "drafts.ready"):
        assert marker in dispatch + writing + read(ROOT / "agents/novel-agent.md")
    assert "full.repair" in dispatch
    assert "Reader" in review
    assert "drafts/vol-N-ch-M.md" in writing
    assert "texts/vol-N-ch-M.md" in review
    assert "target_chars: 4000" in prompt
    assert "min_chars: 3200" in prompt
    assert "一次负责一个完整幕或一个连续叙事批次" in prompt_agent
    assert "用户明确提出审核提示词" in prompt_reviewer
    assert "independent" in writer.lower() or "独立" in writer
    assert "Fast" in anti_ai_agent and "Reader" in anti_ai_agent
    assert "anti-AI" in read(ROOT / "knowledge/anti-ai/index.md")

    # This is a creative-writing runtime. Static tests may protect loading and
    # file boundaries, but active instructions must require semantic reading
    # instead of introducing prompt hashes or automated literary gates.
    creative_contract = skill + dispatch + prompt + writing + review + reader + completion
    for marker in (
        "中文长篇小说创作",
        "真实阅读体验",
        "脚本服务",
        "行动",
        "HARD FIX: synopsis delivery",
        "整体复读",
        "先读正文",
    ):
        assert marker in creative_contract, marker
    for forbidden in ("prompt-manifest", "validate_artifacts", "source_chapter_sha256"):
        assert forbidden not in creative_contract, forbidden
    writer_base = read(ROOT / "templates/runtime/novel-base.md")
    writer_runtime = writing + writer + writer_base
    assert "主代理" in writer_base
    assert "模板" in writer_base
    assert "单章 writer base" in writer_runtime
    assert "目标 Prompt" in writer_runtime
    assert "不得用关键词搜索" in completion

    for marker in ("operation: prompt.create", "batch:", "chapters: [26, 30]", "vol-1-ch-30", "status: pending"):
        assert marker in prompt_batch, marker
    for marker in ("status: interrupted", "status: completed", "status: failed", "status: pending"):
        assert marker in interrupted_fast, marker

    assert "skills/prompt.md" not in frontmatter_paths(ROOT / "agents/prompt-reviewer.md")

    prompt_fixture = read(ROOT / "tests/fixtures/shapes/prompt.chapter.example.md")
    for marker in (
        "prompt_contract: 2",
        "## 人物发动机",
        "## 场景推进",
        "行动与反制",
        "转折与选择",
        "可见结果",
        "下一步触发",
    ):
        assert marker in prompt_fixture, marker

    for markdown in ROOT.rglob("*.md"):
        assert len(re.findall(r"(?m)^```", read(markdown))) % 2 == 0, markdown

    print("skill contract consistency test passed")


if __name__ == "__main__":
    main()
