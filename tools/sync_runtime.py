#!/usr/bin/env python3
"""Synchronize the current novel-pro runtime into a current project."""

import argparse
import os
import re
import stat
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from runtime_manifest import runtime_entries

for stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


SOURCE_FILE = Path(".agent") / ".runtime-source"
CURRENT_RUNTIME_PROFILE = "novel-pro-0.2"
REQUIRED_MIGRATION_FIELDS = (
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
)


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def is_relative_to(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except (ValueError, OSError):
        return False


def looks_like_skill_root(path):
    path = Path(path)
    markers = ("SKILL.md", "skill.json", "agents", "skills", "knowledge", "tools")
    return path.is_dir() and sum((path / marker).exists() for marker in markers) >= 5


def story_version(project_root):
    story = project_root / "story.md"
    if not story.is_file():
        return None
    match = re.search(
        r"(?m)^[ \t]*-?[ \t]*skill_version[ \t]*:[ \t]*['\"]?([^'\"\s]+)",
        read_text(story),
    )
    return match.group(1) if match else None


def runtime_profile(project_root):
    story = project_root / "story.md"
    if not story.is_file():
        return None
    match = re.search(
        r"(?m)^[ \t]*-?[ \t]*runtime_profile[ \t]*:[ \t]*['\"]?([^'\"\s]+)",
        read_text(story),
    )
    return match.group(1) if match else None


def validate_project_root(project_root, skill_root):
    if not project_root.is_dir():
        raise SystemExit(f"project directory does not exist: {project_root}")
    if is_relative_to(project_root, skill_root):
        raise SystemExit("project directory must not be inside the skill source")
    if (project_root / "story.yaml").exists():
        raise SystemExit(
            "检测到旧版本项目(story.yaml)；novel-pro 不再直接兼容旧项目，"
            "请先运行 tools/migrate.py 完整迁移"
        )
    version = story_version(project_root)
    if not version or not version.startswith("5."):
        raise SystemExit(
            "检测到旧版本或无效项目；请先运行 tools/migrate.py 完整迁移，"
            "story.md 必须包含 skill_version: 5.x"
        )
    profile = runtime_profile(project_root)
    status = project_root / ".agent/status.yaml"
    status_text = read_text(status) if status.is_file() else ""
    has_migration_fields = all(
        re.search(rf"(?m)^  {re.escape(field)}:", status_text)
        for field in REQUIRED_MIGRATION_FIELDS
    )
    if profile != CURRENT_RUNTIME_PROFILE or not status.is_file() or not has_migration_fields:
        raise SystemExit(
            "检测到旧版本项目；novel-pro 不再直接同步旧项目，"
            "请先运行 tools/migrate.py <旧项目> <新项目> 完整迁移"
        )
    if re.search(r"(?m)^\s+step:\s*migration\.review\s*$", status_text) or re.search(
        r"(?m)^\s+state:\s*review\s*$", status_text
    ):
        raise SystemExit(
            "项目仍处于 migration.review；请先核对 .migration/report.md，"
            "再运行 tools/migrate.py finalize <新项目>"
        )


def resolve_skill_root(project_root, cli_skill_root):
    candidates = []
    if cli_skill_root:
        candidates.append(Path(cli_skill_root))
    if os.environ.get("NOVEL_SKILL_HOME"):
        candidates.append(Path(os.environ["NOVEL_SKILL_HOME"]))
    source_file = project_root / SOURCE_FILE
    if source_file.is_file():
        candidates.append(Path(read_text(source_file).strip()))
    for candidate in candidates:
        try:
            candidate = candidate.expanduser().resolve()
        except OSError:
            continue
        if looks_like_skill_root(candidate):
            return candidate
    raise SystemExit("cannot locate skill source; pass --skill-root")


def rewrite_runtime_paths(content):
    content = re.sub(
        r"(?<![A-Za-z0-9_./-])skills/",
        ".claude/skill-resources/skills/",
        content,
    )
    content = re.sub(
        r"(?<![A-Za-z0-9_./-])knowledge/",
        ".claude/skill-resources/knowledge/",
        content,
    )
    content = re.sub(
        r"(?<![A-Za-z0-9_./-])agents/",
        ".claude/agents/",
        content,
    )
    content = re.sub(
        r"(?<![A-Za-z0-9_./-])templates/runtime/",
        ".claude/skill-resources/templates/",
        content,
    )
    return content


def desired_runtime(skill_root):
    for source, rel, kind in runtime_entries(skill_root):
        if not source.is_file():
            continue
        data = (
            rewrite_runtime_paths(read_text(source)).encode("utf-8")
            if kind in {"agent", "skill", "knowledge", "template"}
            else source.read_bytes()
        )
        yield rel, data


def runtime_status(project_root, manifest):
    missing, changed = [], []
    for rel, data in manifest:
        target = project_root / rel
        if not target.is_file():
            missing.append(rel.as_posix())
        elif target.read_bytes() != data:
            changed.append(rel.as_posix())
    return missing, changed


def assert_safe_runtime_path(rel):
    if not rel.parts or rel.parts[0] not in {".claude", "tools"}:
        raise RuntimeError(f"refusing to modify non-runtime path: {rel.as_posix()}")


def make_writable(path):
    if path.exists():
        path.chmod(path.stat().st_mode | stat.S_IWRITE)


def atomic_write_bytes(target, data, suffix):
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + suffix)
    try:
        temp.write_bytes(data)
        make_writable(target)
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink()


def write_runtime(project_root, manifest):
    updated = []
    for rel, data in manifest:
        assert_safe_runtime_path(rel)
        target = project_root / rel
        if target.is_file() and target.read_bytes() == data:
            continue
        atomic_write_bytes(target, data, ".tmp-sync")
        updated.append(rel.as_posix())
    return updated


def parse_args():
    parser = argparse.ArgumentParser(description="Sync the current novel-pro v0.2 runtime")
    parser.add_argument("project_root")
    parser.add_argument("--skill-root")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    skill_root = resolve_skill_root(project_root, args.skill_root)
    validate_project_root(project_root, skill_root)

    try:
        manifest = list(desired_runtime(skill_root))
        if not manifest:
            raise ValueError("skill contains no runtime resources")
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc

    missing, changed = runtime_status(project_root, manifest)
    source_change = (
        not (project_root / SOURCE_FILE).is_file()
        or read_text(project_root / SOURCE_FILE).strip() != str(skill_root)
    )
    needs_sync = bool(missing or changed or source_change)

    if args.check:
        if not needs_sync:
            print("runtime resources are current")
            return
        print("runtime resources need synchronization")
        for rel in missing:
            print(f"  - missing: {rel}")
        for rel in changed:
            print(f"  - changed: {rel}")
        if source_change:
            print("  - runtime source: update")
        raise SystemExit(1)

    if args.dry_run:
        print(f"project: {project_root}")
        print(f"source: {skill_root}")
        print("synchronization required" if needs_sync else "runtime resources are current")
        return

    updated = write_runtime(project_root, manifest)
    (project_root / SOURCE_FILE).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(project_root / SOURCE_FILE, f"{skill_root}\n".encode("utf-8"), ".tmp-sync")
    print(f"sync complete: updated {len(updated)}")


if __name__ == "__main__":
    main()
