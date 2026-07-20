#!/usr/bin/env python3
"""Deployment surface for the novel-pro v0.2 project runtime."""

from pathlib import Path


AGENT_FILES = [
    "act-planner.md",
    "anti-ai.md",
    "chapter-planner.md",
    "completion-editor.md",
    "completion-reviewer.md",
    "novel-agent.md",
    "prompt-crafter.md",
    "prompt-reviewer.md",
    "reader.md",
    "volume-planner.md",
    "writer.md",
]

TEMPLATE_FILES = ["novel-base.md"]

SKILL_FILES = [
    "act-planning.md",
    "completion-quality.md",
    "dispatch.md",
    "edit-boundary.md",
    "migration.md",
    "planning.md",
    "prompt.md",
    "review-archive.md",
    "volume-alignment.md",
    "writing.md",
]

PROJECT_TOOL_FILES = ["migrate.py", "runtime_manifest.py", "sync_runtime.py"]


def agent_target(name):
    return Path(".claude") / "agents" / name


def skill_target(name):
    return Path(".claude") / "skill-resources" / "skills" / name


def knowledge_target(name):
    return Path(".claude") / "skill-resources" / "knowledge" / name


def template_target(name):
    return Path(".claude") / "skill-resources" / "templates" / name


def tool_target(name):
    return Path("tools") / name


def runtime_entries(skill_root):
    skill_root = Path(skill_root)
    for name in AGENT_FILES:
        yield skill_root / "agents" / name, agent_target(name), "agent"
    for name in SKILL_FILES:
        yield skill_root / "skills" / name, skill_target(name), "skill"
    for source in sorted((skill_root / "knowledge").rglob("*.md")):
        name = source.relative_to(skill_root / "knowledge").as_posix()
        yield source, knowledge_target(name), "knowledge"
    for name in TEMPLATE_FILES:
        yield skill_root / "templates" / "runtime" / name, template_target(name), "template"
    for name in PROJECT_TOOL_FILES:
        yield skill_root / "tools" / name, tool_target(name), "tool"


def runtime_target_paths():
    return [target.as_posix() for _source, target, _kind in runtime_entries(Path("."))]
