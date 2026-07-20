#!/usr/bin/env python3
"""Rebuild a legacy novel project into a fresh novel-pro project."""

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

for stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


CURRENT_RUNTIME_PROFILE = "novel-pro-0.2"
CURRENT_SKILL_VERSION = "5.2"
SOURCE_FILE = Path(".agent") / ".runtime-source"
REPORT_DIR = Path(".migration")
REPORT_JSON = REPORT_DIR / "report.json"
REPORT_MD = REPORT_DIR / "report.md"

CONTENT_ROOTS = ("settings", "volumes", "acts", "chapters", "prompts", "drafts", "texts")
REQUIRED_CONTENT_FILES = (
    "story.md",
    "settings/genre-setting.md",
    "settings/world-setting.md",
    "settings/writing-style.md",
    "settings/writing-preferences.md",
    "settings/foreshadowing.md",
    "settings/timeline.md",
)
PROJECT_SCAFFOLD_FILES = (
    "CLAUDE.md",
    ".agent/status.yaml",
    ".agent/order.yaml",
    ".agent/run-log.yaml",
)
CONTROL_FILES = {
    "CLAUDE.md",
    ".agent/status.yaml",
    ".agent/order.yaml",
    ".agent/run-log.yaml",
    ".agent/.runtime-source",
}
NORMAL_STEPS = {
    "outline.volume",
    "outline.acts",
    "outline.chapters",
    "prompts.ready",
    "draft.write",
    "drafts.ready",
    "review",
    "volume.complete",
    "book.complete",
}
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


def write_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def atomic_write_text(path, content, suffix):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + suffix)
    try:
        temp.write_text(content, encoding="utf-8")
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


def path_is_within(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except (ValueError, OSError):
        return False


def looks_like_skill_root(path):
    path = Path(path)
    markers = (
        "SKILL.md",
        "skill.json",
        "agents",
        "skills",
        "knowledge",
        "templates",
        "tools",
    )
    return path.is_dir() and sum((path / marker).exists() for marker in markers) >= 6


def is_current_skill_root(path):
    path = Path(path)
    return looks_like_skill_root(path) and (path / "tools/init.py").is_file() and (path / "tools/migrate.py").is_file()


def resolve_skill_root(source_project, cli_skill_root):
    candidates = []
    if cli_skill_root:
        candidates.append(Path(cli_skill_root))
    if os.environ.get("NOVEL_SKILL_HOME"):
        candidates.append(Path(os.environ["NOVEL_SKILL_HOME"]))

    script_root = Path(__file__).resolve().parent.parent
    candidates.append(script_root)
    invoking_source_file = script_root / SOURCE_FILE
    if invoking_source_file.is_file():
        candidates.append(Path(read_text(invoking_source_file).strip()))

    source_file = Path(source_project) / SOURCE_FILE
    if source_file.is_file():
        candidates.append(Path(read_text(source_file).strip()))

    seen = set()
    for candidate in candidates:
        try:
            candidate = candidate.expanduser().resolve()
        except OSError:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        if is_current_skill_root(candidate):
            return candidate
    raise SystemExit("找不到当前 novel-pro 开发版；请通过 --skill-root 指定技能目录。")


def story_value(project_root, key):
    project_root = Path(project_root)
    pattern = re.compile(
        rf"(?m)^[ \t]*-?[ \t]*{re.escape(key)}[ \t]*:[ \t]*['\"]?([^'\"\s]+)"
    )
    for name in ("story.md", "story.yaml"):
        story = project_root / name
        if not story.is_file():
            continue
        match = pattern.search(read_text(story))
        if match:
            return match.group(1)
    return None


def source_version(source_project):
    return story_value(source_project, "skill_version") or "unknown"


def source_profile(source_project):
    return story_value(source_project, "runtime_profile") or "missing"


def has_migration_fields(status_text):
    return all(
        re.search(rf"(?m)^  {re.escape(field)}:", status_text)
        for field in REQUIRED_MIGRATION_FIELDS
    )


def validate_source(source_project, skill_root, target_project):
    if not source_project.is_dir() or source_project.is_symlink():
        raise SystemExit(f"旧项目目录无效: {source_project}")
    if path_is_within(source_project, skill_root):
        raise SystemExit("旧项目不能位于 novel-pro 技能源目录内。")
    if looks_like_skill_root(source_project):
        raise SystemExit("源目录看起来是 novel-pro 技能源目录，不是小说项目。")
    if source_project == target_project:
        raise SystemExit("旧项目和迁移目标不能是同一个目录。")
    if path_is_within(target_project, source_project):
        raise SystemExit("迁移目标不能位于旧项目目录内。")
    if path_is_within(source_project, target_project):
        raise SystemExit("旧项目不能位于迁移目标目录内。")
    if not (source_project / "story.md").is_file() and not (source_project / "story.yaml").is_file():
        raise SystemExit("源目录缺少 story.md 或 story.yaml，无法识别为旧小说项目。")
    profile = source_profile(source_project)
    status = source_project / ".agent/status.yaml"
    if profile == CURRENT_RUNTIME_PROFILE and status.is_file() and has_migration_fields(read_text(status)):
        raise SystemExit("源项目已经是当前 novel-pro profile，无需迁移；请使用当前项目流程。")


def validate_target(target_project, skill_root):
    if target_project.is_symlink():
        raise SystemExit("迁移目标不能是符号链接。")
    if path_is_within(target_project, skill_root):
        raise SystemExit("迁移目标不能位于 novel-pro 技能源目录内。")
    if target_project.exists() and not target_project.is_dir():
        raise SystemExit("迁移目标不是目录。")
    if target_project.is_dir() and any(target_project.iterdir()):
        raise SystemExit("迁移目标必须是不存在的目录或空目录。")


def detect_genre(source_project, override):
    if override and override.strip():
        return override.strip()
    genre_file = source_project / "settings/genre-setting.md"
    if genre_file.is_file():
        match = re.search(r"(?m)^\s*-?\s*genre_id\s*:\s*([^\s]+)", read_text(genre_file))
        if match and match.group(1) not in {"TODO", "{{genre_id}}"}:
            return match.group(1).strip("`\"'")
    return "unknown"


def load_runtime_targets(skill_root):
    manifest_path = skill_root / "tools/runtime_manifest.py"
    spec = importlib.util.spec_from_file_location("novel_pro_runtime_manifest", manifest_path)
    if spec is None or spec.loader is None:
        return set()
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {target.as_posix() for _source, target, _kind in module.runtime_entries(skill_root)}


def iter_source_files(source_project):
    for path in sorted(source_project.rglob("*"), key=lambda item: item.as_posix()):
        rel = path.relative_to(source_project)
        if path.is_symlink():
            yield path, rel, "symlink"
        elif path.is_file():
            yield path, rel, "file"


def is_content_path(rel):
    rel_text = rel.as_posix()
    return rel_text == "story.md" or any(
        rel.parts and rel.parts[0] == root for root in CONTENT_ROOTS
    )


def classify_unmapped(rel, runtime_targets):
    rel_text = rel.as_posix()
    if rel_text in CONTROL_FILES or rel_text in runtime_targets:
        return "legacy-runtime", True
    if rel_text == "story.yaml":
        return "legacy-story-format", False
    if rel.parts and rel.parts[0] == ".agent" and len(rel.parts) > 1 and rel.parts[1] == "tasks":
        return "task-history", False
    return "manual-review", False


def replace_story_key(lines, key, value):
    pattern = re.compile(rf"^([ \t]*-?[ \t]*{re.escape(key)}[ \t]*:[ \t]*).*$")
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            lines[index] = match.group(1) + value
            return True
    return False


def insert_story_metadata(lines, missing):
    if not missing:
        return
    metadata = [f"- {key}: {value}" for key, value in missing]
    heading_index = next((i for i, line in enumerate(lines) if line.strip() == "## 元信息"), None)
    if heading_index is not None:
        lines[heading_index + 1:heading_index + 1] = metadata
        return
    first_heading = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    insert_at = first_heading + 1 if first_heading is not None else 0
    lines[insert_at:insert_at] = ["", "## 元信息", *metadata, ""]


def normalize_story(source_story, target_project_name, genre, fallback):
    content = read_text(source_story).strip() if source_story.is_file() and not source_story.is_symlink() else fallback.strip()
    if not content:
        content = fallback.strip()
    if not content:
        return fallback
    lines = content.splitlines()
    has_title = False
    for index, line in enumerate(lines):
        if line.startswith("# "):
            lines[index] = f"# {target_project_name}"
            has_title = True
            break
    if not has_title:
        lines.insert(0, f"# {target_project_name}")
    missing = []
    if not replace_story_key(lines, "skill_version", CURRENT_SKILL_VERSION):
        missing.append(("skill_version", CURRENT_SKILL_VERSION))
    if not replace_story_key(lines, "runtime_profile", CURRENT_RUNTIME_PROFILE):
        missing.append(("runtime_profile", CURRENT_RUNTIME_PROFILE))
    if genre != "unknown" and not replace_story_key(lines, "题材", genre):
        missing.append(("题材", genre))
    insert_story_metadata(lines, missing)
    result = "\n".join(lines).rstrip() + "\n"
    return result


def normalize_claude(staging, target_project_name):
    path = staging / "CLAUDE.md"
    lines = read_text(path).splitlines()
    staging_prefix = f"# {staging.name}"
    for index, line in enumerate(lines):
        if line.startswith("# "):
            suffix = line[len(staging_prefix):] if line.startswith(staging_prefix) else ""
            lines[index] = f"# {target_project_name}{suffix}"
            break
    atomic_write_text(path, "\n".join(lines).rstrip() + "\n", ".tmp-migration")


def read_cursor_values(source_project):
    status = source_project / ".agent/status.yaml"
    if not status.is_file():
        return {}
    values = {}
    in_cursor = False
    for line in read_text(status).splitlines():
        if line == "cursor:":
            in_cursor = True
            continue
        if in_cursor and line and not line.startswith(" "):
            break
        if not in_cursor:
            continue
        match = re.match(r"^  (volume|act|range|paused_reason):\s*(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def resume_step(source_project):
    status = source_project / ".agent/status.yaml"
    if status.is_file():
        match = re.search(r"(?m)^\s+step:\s*([^\s]+)", read_text(status))
        if match and match.group(1) in NORMAL_STEPS:
            return match.group(1)
    return "outline.volume"


def yaml_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if value in NORMAL_STEPS or value in {"none", "review", "complete", "report", "pending", "not_started"}:
        return value
    return json.dumps(str(value), ensure_ascii=False)


def replace_status_fields(content, cursor_values=None, migration_values=None):
    cursor_values = cursor_values or {}
    migration_values = migration_values or {}
    lines = content.splitlines()
    block = None
    for index, line in enumerate(lines):
        if line and not line.startswith(" ") and line.endswith(":"):
            block = line[:-1]
        if block == "cursor" and line.startswith("  "):
            match = re.match(r"^  ([A-Za-z_]+):", line)
            if match and match.group(1) in cursor_values:
                lines[index] = f"  {match.group(1)}: {cursor_values[match.group(1)]}"
        if block == "migration" and line.startswith("  "):
            match = re.match(r"^  ([A-Za-z_]+):", line)
            if match and match.group(1) in migration_values:
                lines[index] = f"  {match.group(1)}: {yaml_value(migration_values[match.group(1)])}"
    return "\n".join(lines).rstrip() + "\n"


def copy_source_content(source_project, staging, target_project_name, skill_root, genre):
    transferred = []
    unmapped = []
    legacy_runtime = []
    runtime_targets = load_runtime_targets(skill_root)
    source_story = source_project / "story.md"
    target_story = staging / "story.md"
    target_story.write_text(
        normalize_story(source_story, target_project_name, genre, read_text(target_story)),
        encoding="utf-8",
    )
    if source_story.is_file() and not source_story.is_symlink():
        transferred.append({"source": "story.md", "target": "story.md", "kind": "normalized"})
    legacy_story = source_project / "story.yaml"
    if legacy_story.is_file() and not legacy_story.is_symlink():
        archived_story = staging / REPORT_DIR / "legacy/story.yaml"
        archived_story.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_story, archived_story)
        transferred.append(
            {
                "source": "story.yaml",
                "target": (REPORT_DIR / "legacy/story.yaml").as_posix(),
                "kind": "preserved-for-review",
            }
        )

    for path, rel, path_kind in iter_source_files(source_project):
        rel_text = rel.as_posix()
        if rel_text in {"story.md", "story.yaml"}:
            continue
        if path_kind == "symlink":
            item = {"path": rel_text, "category": "symlink", "reason": "符号链接未跟随复制"}
            unmapped.append(item)
            continue
        if is_content_path(rel):
            target = staging / rel
            if target.is_symlink():
                raise RuntimeError(f"迁移目标路径是符号链接: {rel_text}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            transferred.append({"source": rel_text, "target": rel_text, "kind": "copied"})
            continue
        category, cleanable = classify_unmapped(rel, runtime_targets)
        item = {"path": rel_text, "category": category}
        unmapped.append(item)
        if cleanable:
            legacy_runtime.append({"path": rel_text, "reason": category})

    missing = []
    for rel_text in REQUIRED_CONTENT_FILES:
        source_path = source_project / rel_text
        if not source_path.is_file() or source_path.is_symlink():
            reason = "源项目缺少对应文件；目标保留新版初始化文件"
            if rel_text == "story.md" and (source_project / "story.yaml").is_file():
                reason = "源项目只有旧版 story.yaml，未自动猜测其结构"
            missing.append({"path": rel_text, "reason": reason})

    missing_runtime = [
        {
            "path": rel_text,
            "reason": "旧项目未提供；由当前 novel-pro 初始化重新生成",
        }
        for rel_text in sorted(runtime_targets)
        if not (source_project / rel_text).is_file() or (source_project / rel_text).is_symlink()
    ]
    missing_project = [
        {
            "path": rel_text,
            "reason": "旧项目未提供；由当前 novel-pro 初始化重新生成",
        }
        for rel_text in PROJECT_SCAFFOLD_FILES
        if not (source_project / rel_text).is_file() or (source_project / rel_text).is_symlink()
    ]

    return transferred, missing, missing_project, missing_runtime, unmapped, legacy_runtime


def run_initializer(skill_root, staging, genre):
    command = [
        sys.executable,
        "-B",
        str(skill_root / "tools/init.py"),
        str(staging),
        "--genre-name",
        genre,
    ]
    environment = os.environ.copy()
    environment["NOVEL_SKILL_HOME"] = str(skill_root)
    result = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=environment,
    )
    if result.returncode:
        details = (result.stdout + "\n" + result.stderr).strip()
        raise RuntimeError(f"新项目初始化失败: {details}")


def publish_staging(staging, target):
    if not target.exists():
        staging.rename(target)
        return
    moved = []
    try:
        for child in list(staging.iterdir()):
            destination = target / child.name
            if destination.exists() or destination.is_symlink():
                raise RuntimeError(f"迁移目标在构建期间发生变化: {destination}")
            child.rename(destination)
            moved.append(destination)
        staging.rmdir()
    except Exception:
        for destination in reversed(moved):
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            elif destination.exists() or destination.is_symlink():
                destination.unlink()
        raise


def report_data(
    source_project,
    target_project,
    source_version_text,
    source_profile_text,
    genre,
    resume,
    transferred,
    missing,
    missing_project,
    missing_runtime,
    unmapped,
    legacy_runtime,
    staging,
):
    active_files = sum(
        1
        for path in staging.rglob("*")
        if path.is_file() and REPORT_DIR not in path.relative_to(staging).parents
    )
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "format": 1,
        "state": "review",
        "created_at": timestamp,
        "source_project": str(source_project),
        "target_project": str(target_project),
        "source_version": source_version_text,
        "source_profile": source_profile_text,
        "target_version": CURRENT_SKILL_VERSION,
        "target_profile": CURRENT_RUNTIME_PROFILE,
        "genre": genre,
        "resume_step": resume,
        "completed_files": transferred,
        "missing_files": missing,
        "missing_project_files": missing_project,
        "missing_runtime_files": missing_runtime,
        "unmapped_files": unmapped,
        "legacy_runtime_files": legacy_runtime,
        "created_active_file_count": active_files,
        "cleanup": {
            "state": "pending",
            "candidates": [item["path"] for item in legacy_runtime],
            "cleaned": [],
            "skipped": [],
        },
    }


def render_report(report):
    cleanup = report.get("cleanup", {})
    lines = [
        "# novel-pro 项目迁移报告",
        "",
        f"- 状态: `{report.get('state', 'unknown')}`",
        f"- 源项目: `{report['source_project']}`",
        f"- 目标项目: `{report['target_project']}`",
        f"- 源版本: `{report['source_version']}` / profile `{report['source_profile']}`",
        f"- 目标版本: `{report['target_version']}` / profile `{report['target_profile']}`",
        f"- 恢复阶段: `{report['resume_step']}`",
        "",
        "## 已完成文件",
        "",
    ]
    completed = report.get("completed_files", [])
    lines.extend(
        f"- `{item['source']}` → `{item['target']}` ({item['kind']})" for item in completed
    )
    if not completed:
        lines.append("- 无")
    lines.extend(["", "## 对比新版技能缺失的内容文件", ""])
    missing = report.get("missing_files", [])
    lines.extend(f"- `{item['path']}`：{item['reason']}" for item in missing)
    if not missing:
        lines.append("- 无")
    lines.extend(["", "## 对比新版技能缺失的项目骨架文件", ""])
    missing_project = report.get("missing_project_files", [])
    lines.extend(f"- `{item['path']}`：{item['reason']}" for item in missing_project)
    if not missing_project:
        lines.append("- 无")
    lines.extend(["", "## 对比新版技能缺失的运行时文件", ""])
    missing_runtime = report.get("missing_runtime_files", [])
    lines.extend(f"- `{item['path']}`：{item['reason']}" for item in missing_runtime)
    if not missing_runtime:
        lines.append("- 无")
    lines.extend(["", "## 未自动搬运的旧项目文件", ""])
    unmapped = report.get("unmapped_files", [])
    lines.extend(f"- `{item['path']}`：{item['category']}" for item in unmapped)
    if not unmapped:
        lines.append("- 无")
    lines.extend(["", "## 旧版本文件清理", ""])
    lines.append(f"- 清理状态: `{cleanup.get('state', 'pending')}`")
    candidates = cleanup.get("candidates", [])
    if candidates:
        lines.append("- 可安全清理的旧运行时文件:")
        lines.extend(f"  - `{item}`" for item in candidates)
    else:
        lines.append("- 没有可自动清理的旧运行时文件。")
    cleaned = cleanup.get("cleaned", [])
    if cleaned:
        lines.append("- 已清理:")
        lines.extend(f"  - `{item}`" for item in cleaned)
    skipped = cleanup.get("skipped", [])
    if skipped:
        lines.append("- 跳过:")
        lines.extend(f"  - `{item}`" for item in skipped)
    lines.extend(
        [
            "",
            "## 后续操作",
            "",
            "源项目在报告核对前保持不变。确认迁移内容后执行:",
            "",
            f'`python tools/migrate.py finalize "{report["target_project"]}"`',
            f'`python tools/migrate.py cleanup "{report["target_project"]}" --confirm`',
            "",
            "清理只删除报告列出的旧运行时文件，不删除正文、规划、设定、任务历史或人工未映射文件。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_report(target_project, report):
    report_dir = target_project / REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json = report_dir / REPORT_JSON.name
    report_md = report_dir / REPORT_MD.name
    atomic_write_text(
        report_json,
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        ".tmp-migration",
    )
    atomic_write_text(report_md, render_report(report), ".tmp-migration")


def create_migration(args):
    source = Path(args.source_project).expanduser().resolve()
    target = Path(args.target_project).expanduser().resolve()
    skill_root = resolve_skill_root(source, args.skill_root)
    validate_source(source, skill_root, target)
    validate_target(target, skill_root)
    target.parent.mkdir(parents=True, exist_ok=True)

    genre = detect_genre(source, args.genre)
    source_cursor = read_cursor_values(source)
    resume = resume_step(source)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.migration-", dir=str(target.parent)))
    try:
        run_initializer(skill_root, staging, genre)
        normalize_claude(staging, target.name)
        transferred, missing, missing_project, missing_runtime, unmapped, legacy_runtime = copy_source_content(
            source, staging, target.name, skill_root, genre
        )
        report = report_data(
            source,
            target,
            source_version(source),
            source_profile(source),
            genre,
            resume,
            transferred,
            missing,
            missing_project,
            missing_runtime,
            unmapped,
            legacy_runtime,
            staging,
        )
        write_report(staging, report)
        status_path = staging / ".agent/status.yaml"
        migration_values = {
            "state": "review",
            "phase": "report",
            "source_project": str(source),
            "source_version": source_version(source),
            "target_project": str(target),
            "report_path": REPORT_MD.as_posix(),
            "resume_step": resume,
            "cleanup": "pending",
            "completed_count": len(transferred),
            "missing_count": len(missing) + len(missing_project) + len(missing_runtime),
            "unmapped_count": len(unmapped),
        }
        atomic_write_text(
            status_path,
            replace_status_fields(status_path.read_text(encoding="utf-8"), source_cursor | {"step": "migration.review"}, migration_values),
            ".tmp-migration",
        )
        publish_staging(staging, target)
    except (OSError, RuntimeError) as exc:
        raise SystemExit(f"迁移失败: {exc}") from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    print(f"迁移项目已创建: {target}")
    print(f"迁移报告: {target / REPORT_MD}")
    print(f"已完成文件: {len(transferred)}")
    print(f"新版缺失文件: {len(missing) + len(missing_project) + len(missing_runtime)}")
    print(f"未自动搬运文件: {len(unmapped)}")
    print("源项目未修改；请先核对报告，再执行 finalize 和 cleanup。")


def load_report(target):
    report_path = target / REPORT_JSON
    if not report_path.is_file():
        raise SystemExit(f"缺少迁移报告: {report_path}")
    try:
        return json.loads(read_text(report_path))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"迁移报告格式无效: {report_path}") from exc


def update_target_status(target, cursor_values=None, migration_values=None):
    status_path = target / ".agent/status.yaml"
    if not status_path.is_file():
        raise SystemExit(f"目标项目缺少状态文件: {status_path}")
    content = replace_status_fields(
        read_text(status_path),
        cursor_values=cursor_values,
        migration_values=migration_values,
    )
    atomic_write_text(status_path, content, ".tmp-migration")


def finalize_migration(args):
    target = Path(args.target_project).expanduser().resolve()
    if not target.is_dir() or target.is_symlink():
        raise SystemExit(f"目标项目目录无效: {target}")
    report = load_report(target)
    if report.get("state") == "complete":
        print("迁移已经 finalize，无需重复执行。")
        return
    resume = report.get("resume_step", "outline.volume")
    if resume not in NORMAL_STEPS:
        resume = "outline.volume"
    update_target_status(
        target,
        cursor_values={"step": resume},
        migration_values={"state": "complete", "phase": "complete", "cleanup": "pending"},
    )
    report["state"] = "complete"
    report["finalized_at"] = datetime.now(timezone.utc).isoformat()
    write_report(target, report)
    print(f"迁移已确认: {target}")
    print("旧项目仍未修改；如需清理旧运行时文件，请执行 cleanup --confirm。")


def cleanup_migration(args):
    target = Path(args.target_project).expanduser().resolve()
    if not target.is_dir() or target.is_symlink():
        raise SystemExit(f"目标项目目录无效: {target}")
    report = load_report(target)
    if report.get("state") != "complete":
        raise SystemExit("请先核对迁移报告并执行 finalize，再清理旧版本文件。")
    if not args.confirm:
        candidates = report.get("cleanup", {}).get("candidates", [])
        print("将清理以下旧运行时文件:")
        for item in candidates:
            print(f"  - {item}")
        raise SystemExit("清理是显式操作；确认后添加 --confirm。")

    source = Path(report["source_project"]).expanduser().resolve()
    if not source.is_dir() or source.is_symlink():
        raise SystemExit(f"源项目不存在或不是普通目录: {source}")
    cleaned = []
    skipped = []
    for rel_text in report.get("cleanup", {}).get("candidates", []):
        path = source / Path(rel_text)
        if not path_is_within(path, source) or path == source:
            skipped.append(rel_text)
            continue
        if path.is_symlink() or not path.is_file():
            skipped.append(rel_text)
            continue
        path.unlink()
        cleaned.append(rel_text)
        parent = path.parent
        while parent != source and path_is_within(parent, source):
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    cleanup = report.setdefault("cleanup", {})
    cleanup["state"] = "complete"
    cleanup["cleaned"] = sorted(set(cleanup.get("cleaned", []) + cleaned))
    cleanup["skipped"] = sorted(set(cleanup.get("skipped", []) + skipped))
    cleanup["completed_at"] = datetime.now(timezone.utc).isoformat()
    write_report(target, report)
    update_target_status(target, migration_values={"cleanup": "complete"})
    print(f"旧版本运行时文件清理完成: {len(cleaned)}")
    if skipped:
        print(f"跳过未删除文件: {len(skipped)}；详见 {target / REPORT_MD}")


def parser_for_command():
    parser = argparse.ArgumentParser(
        description="novel-pro 完整项目迁移：重建新项目、搬运内容、报告差异并按确认清理旧运行时文件。"
    )
    subparsers = parser.add_subparsers(dest="command")

    create = subparsers.add_parser("create", help="从旧项目重建迁移项目")
    create.add_argument("source_project")
    create.add_argument("target_project")
    create.add_argument("--skill-root")
    create.add_argument("--genre", help="覆盖从旧项目检测到的题材编号")

    finalize = subparsers.add_parser("finalize", help="确认迁移报告并恢复正常创作阶段")
    finalize.add_argument("target_project")

    cleanup = subparsers.add_parser("cleanup", help="清理报告列出的旧版本运行时文件")
    cleanup.add_argument("target_project")
    cleanup.add_argument("--confirm", action="store_true")
    return parser


def parse_args():
    raw = sys.argv[1:]
    if raw and raw[0] not in {"create", "finalize", "cleanup", "-h", "--help"}:
        raw = ["create", *raw]
    parser = parser_for_command()
    args = parser.parse_args(raw)
    if not args.command:
        parser.error("请指定 create、finalize 或 cleanup")
    return args


def main():
    args = parse_args()
    if args.command == "create":
        create_migration(args)
    elif args.command == "finalize":
        finalize_migration(args)
    else:
        cleanup_migration(args)


if __name__ == "__main__":
    main()
