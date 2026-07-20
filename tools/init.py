#!/usr/bin/env python3
"""Initialize a novel-pro v0.2 project."""

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

from _common import is_relative_to, looks_like_skill_root, read_text
from runtime_manifest import runtime_entries

for stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


SKILL_HOME = Path(
    os.environ.get("NOVEL_SKILL_HOME", Path(__file__).resolve().parent.parent)
).resolve()
SOURCE_FILE = Path(".agent") / ".runtime-source"
REQUIRED_SOURCE_FILES = (
    Path("templates/story.md"),
    Path("templates/CLAUDE.md"),
    Path("templates/.agent/status.yaml"),
    Path("templates/.agent/order.yaml"),
    Path("templates/settings/genre-setting.md"),
    Path("templates/settings/world-setting.md"),
    Path("templates/settings/writing-style.md"),
    Path("templates/settings/writing-preferences.md"),
    Path("knowledge/index.md"),
    Path("knowledge/webnovel/index.md"),
    Path("knowledge/genre/index.md"),
    Path("knowledge/plot/index.md"),
    Path("knowledge/character/index.md"),
    Path("knowledge/scene/index.md"),
    Path("knowledge/anti-ai/index.md"),
)

DEFAULT_GENRES = [
    "xianxia", "xuanhuan", "urban", "urban-romance", "urban-farming",
    "urban-brained", "suspense-crime", "suspense-brained", "historical",
    "historical-brained", "ancient-politics", "anti-japanese-war",
    "scifi-apocalypse", "western-fantasy", "war-god", "derivative",
    "male-derivative", "game-sports", "urban-daily", "urban-cultivation",
    "urban-high-martial", "suspense-paranormal", "anime-derivative",
]


def load_genres():
    registry = SKILL_HOME / "knowledge" / "genre" / "index.md"
    if not registry.is_file():
        return DEFAULT_GENRES
    genres = []
    in_table = False
    for line in read_text(registry).splitlines():
        if line.startswith("## "):
            if in_table:
                break
            in_table = line.strip() == "## 题材注册表"
            continue
        if not in_table:
            continue
        match = re.match(r"\|\s*`([^`]+)`\s*\|", line)
        if match and match.group(1) not in genres:
            genres.append(match.group(1))
    return genres or DEFAULT_GENRES


GENRES = load_genres()


def validate_target(project_path):
    project_path = Path(project_path).expanduser()
    if project_path.is_symlink():
        raise SystemExit("错误: 初始化目标不能是符号链接。")
    project_path = project_path.resolve()
    if project_path == SKILL_HOME or is_relative_to(project_path, SKILL_HOME):
        raise SystemExit("错误: 不能在 novel-pro skill 目录内初始化小说项目。")
    if looks_like_skill_root(project_path):
        raise SystemExit("错误: 目标目录看起来是 skill 源目录，拒绝初始化。")
    if project_path.exists() and not project_path.is_dir():
        raise SystemExit("错误: 初始化目标不是目录。")
    if (project_path / "story.yaml").exists():
        raise SystemExit("错误: story.yaml 属于旧版本项目；请先通过 tools/migrate.py 完整迁移。")
    if (project_path / "story.md").exists():
        raise SystemExit("错误: 目标已有 story.md；旧项目请先通过 tools/migrate.py 完整迁移。")
    if project_path.is_dir() and any(project_path.iterdir()):
        raise SystemExit("错误: 初始化目标必须是不存在的目录或空目录；旧项目请使用 tools/migrate.py 完整迁移。")
    return project_path


def validate_skill_source():
    if not SKILL_HOME.is_dir() or not looks_like_skill_root(SKILL_HOME):
        raise SystemExit(f"错误: skill 源目录无效: {SKILL_HOME}")

    missing = [rel.as_posix() for rel in REQUIRED_SOURCE_FILES if not (SKILL_HOME / rel).is_file()]
    entries = list(runtime_entries(SKILL_HOME))
    missing.extend(
        source.relative_to(SKILL_HOME).as_posix()
        for source, _target, _kind in entries
        if not source.is_file()
    )
    targets = [target.as_posix() for _source, target, _kind in entries]
    duplicate_targets = sorted({target for target in targets if targets.count(target) > 1})
    if missing:
        missing = sorted(set(missing))
        raise SystemExit("错误: skill 运行时资源缺失:\n  - " + "\n  - ".join(missing))
    if duplicate_targets:
        raise SystemExit("错误: skill 运行时目标重复:\n  - " + "\n  - ".join(duplicate_targets))
    return entries


def write_if_missing(path, content):
    if path.exists():
        if not path.is_file():
            raise RuntimeError(f"目标路径不是文件: {path}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def copy_if_missing(source, target):
    if target.exists():
        if not target.is_file():
            raise RuntimeError(f"目标路径不是文件: {target}")
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def create_skeleton(project_path):
    for rel in (
        "settings/character-setting", "volumes", "acts", "chapters", "prompts",
        "drafts", "texts", "tools", ".agent/tasks", ".claude/agents",
        ".claude/skill-resources/skills", ".claude/skill-resources/knowledge",
        ".claude/skill-resources/templates",
    ):
        (project_path / rel).mkdir(parents=True, exist_ok=True)


def template_text(rel):
    return (SKILL_HOME / "templates" / rel).read_text(encoding="utf-8")


def deploy_project_files(project_path, genre, project_name):
    story = template_text("story.md")
    story = story.replace("{{project_name}}", project_name).replace("{{genre}}", genre)
    write_if_missing(project_path / "story.md", story)

    genre_text = template_text("settings/genre-setting.md")
    genre_text = genre_text.replace("{{genre_id}}", genre).replace("{{genre}}", genre)
    write_if_missing(project_path / "settings/genre-setting.md", genre_text)
    copy_if_missing(
        SKILL_HOME / "templates/settings/world-setting.md",
        project_path / "settings/world-setting.md",
    )
    copy_if_missing(
        SKILL_HOME / "templates/settings/writing-style.md",
        project_path / "settings/writing-style.md",
    )
    copy_if_missing(
        SKILL_HOME / "templates/settings/writing-preferences.md",
        project_path / "settings/writing-preferences.md",
    )
    write_if_missing(project_path / "settings/character-setting/.gitkeep", "")

    write_if_missing(
        project_path / "settings/foreshadowing.md",
        "# 伏笔追踪\n\n只记录已经进入规划或正文、且会影响后续创作的伏笔。\n",
    )
    write_if_missing(
        project_path / "settings/timeline.md",
        "# 时间线\n\n只记录会影响后续幕章承接的时间事实。\n",
    )
    write_if_missing(project_path / ".agent/status.yaml", template_text(".agent/status.yaml"))
    write_if_missing(project_path / ".agent/order.yaml", template_text(".agent/order.yaml"))
    write_if_missing(project_path / ".agent/run-log.yaml", "runs: []\n")

    claude = template_text("CLAUDE.md")
    claude = claude.replace("{{project_name}}", project_name).replace("{{genre}}", genre)
    write_if_missing(project_path / "CLAUDE.md", claude)


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


def deploy_runtime(project_path, entries):
    for source, rel, kind in entries:
        target = project_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if kind in {"agent", "skill", "knowledge", "template"}:
            target.write_bytes(rewrite_runtime_paths(read_text(source)).encode("utf-8"))
        else:
            shutil.copy2(source, target)
    (project_path / SOURCE_FILE).write_text(str(SKILL_HOME) + "\n", encoding="utf-8")


def remove_path(path):
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def publish_project(staging, project_path):
    if not project_path.exists():
        staging.rename(project_path)
        return

    moved = []
    try:
        for child in list(staging.iterdir()):
            target = project_path / child.name
            if target.exists() or target.is_symlink():
                raise RuntimeError(f"初始化目标在构建期间发生变化: {target}")
            child.rename(target)
            moved.append(target)
    except Exception:
        for target in reversed(moved):
            remove_path(target)
        raise


def validate_agent_paths(project_path):
    errors = []
    for agent in (project_path / ".claude/agents").glob("*.md"):
        frontmatter = read_text(agent).split("---", 2)
        if len(frontmatter) < 3:
            errors.append(f"{agent.name}: missing frontmatter")
            continue
        for value in re.findall(r"^\s*-\s*path:\s*(.+)$", frontmatter[1], re.M):
            rel = value.strip().strip("\"'")
            if "{" in rel or Path(rel).is_absolute() or not (project_path / rel).is_file():
                errors.append(f"{agent.name}: {rel}")
    if errors:
        raise SystemExit("Agent 路径验证失败:\n  - " + "\n  - ".join(errors))


def select_genre():
    for index, genre in enumerate(GENRES, 1):
        print(f"  {index}. {genre}")
    while True:
        try:
            index = int(input(f"选择题材 (1-{len(GENRES)}): ").strip()) - 1
            if 0 <= index < len(GENRES):
                return GENRES[index]
        except EOFError as exc:
            raise SystemExit("未提供题材；请使用 --genre 指定题材编号。") from exc
        except ValueError:
            pass
        print("无效选择。")


def parse_args():
    parser = argparse.ArgumentParser(description="初始化 novel-pro v0.2 小说项目。")
    parser.add_argument("project_path", nargs="?", default=str(Path.cwd()))
    parser.add_argument("--genre", type=int, help=f"题材编号 1-{len(GENRES)}")
    parser.add_argument("--genre-name", help="直接指定题材名称或编号；用于项目迁移时保留原题材。")
    args = parser.parse_args()
    if args.genre is not None and args.genre_name:
        parser.error("--genre 与 --genre-name 不能同时使用")
    if args.genre is not None and not 1 <= args.genre <= len(GENRES):
        parser.error(f"题材编号必须为 1-{len(GENRES)}")
    genre = args.genre_name.strip() if args.genre_name else (GENRES[args.genre - 1] if args.genre else None)
    if genre == "":
        parser.error("--genre-name 不能为空")
    return Path(args.project_path).expanduser(), genre


def main():
    project_path, genre = parse_args()
    project_path = validate_target(project_path)
    entries = validate_skill_source()
    genre = genre or select_genre()
    project_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{project_path.name}.init-", dir=str(project_path.parent)))
    try:
        create_skeleton(staging)
        deploy_project_files(staging, genre, project_path.name)
        deploy_runtime(staging, entries)
        validate_agent_paths(staging)
        publish_project(staging, project_path)
    except (OSError, RuntimeError) as exc:
        raise SystemExit(f"初始化失败: {exc}") from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    print(f"初始化完成: {project_path}")
    print(f"题材: {genre}")
    print("入口: 加载 novel-agent")


if __name__ == "__main__":
    main()
