#!/usr/bin/env python3
"""Runtime file-safety checks for initialization and synchronization."""

import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "tools/init.py"
SYNC = ROOT / "tools/sync_runtime.py"
MIGRATE = ROOT / "tools/migrate.py"


def run(*args, expected=0, env=None):
    result = subprocess.run(args, text=True, encoding="utf-8", capture_output=True, env=env)
    if result.returncode != expected:
        raise AssertionError(
            f"expected {expected}, got {result.returncode}: {' '.join(map(str, args))}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(project, rel, body):
    path = project / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def init(project):
    return run(sys.executable, "-B", str(INIT), str(project), "--genre", "1")


def sync(project, *extra, expected=0):
    return run(sys.executable, "-B", str(SYNC), str(project), *extra, expected=expected)


def migrate(source, target, *extra, expected=0):
    return run(
        sys.executable,
        "-B",
        str(MIGRATE),
        str(source),
        str(target),
        "--skill-root",
        str(ROOT),
        *extra,
        expected=expected,
    )


def main():
    forbidden = ROOT / "should-not-be-created"
    run(sys.executable, "-B", str(INIT), str(forbidden), "--genre", "1", expected=1)
    assert not forbidden.exists()

    with tempfile.TemporaryDirectory(prefix="novel-pro-safety-") as tmp:
        project = Path(tmp) / "project"
        init(project)

        status = (project / ".agent/status.yaml").read_text(encoding="utf-8")
        assert "step: outline.volume" in status
        assert (project / "CLAUDE.md").read_text(encoding="utf-8").startswith(f"# {project.name} -")
        assert (project / "story.md").read_text(encoding="utf-8").startswith(f"# {project.name}\n")
        order = (project / ".agent/order.yaml").read_text(encoding="utf-8")
        assert 'operation: ""' in order and "status: idle" in order

        mounted = project / ".claude"
        assert (mounted / "agents/novel-agent.md").is_file()
        assert not (mounted / "agents/novel-base.md").exists()
        assert (mounted / "skill-resources/templates/novel-base.md").is_file()
        assert (project / "tools/migrate.py").is_file()
        assert (mounted / "skill-resources/skills/migration.md").is_file()
        assert (mounted / "agents/prompt-reviewer.md").is_file()
        for markdown in mounted.rglob("*.md"):
            runtime_body = markdown.read_text(encoding="utf-8")
            assert not re.search(r"(?<![A-Za-z0-9_./`-])skills/", runtime_body), markdown
            assert not re.search(r"(?<![A-Za-z0-9_./`-])knowledge/", runtime_body), markdown
            assert not re.search(r"(?<![A-Za-z0-9_./`-])templates/runtime/", runtime_body), markdown

        protected = {
            ".agent/status.yaml": status,
            ".agent/order.yaml": "user active task\n",
            "story.md": "# user story\n- skill_version: 5.2\n- runtime_profile: novel-pro-0.2\n",
            "settings/world-setting.md": "user world setting\n",
            "volumes/volume-1.md": "user volume outline\n",
            "acts/vol-1-act-1.md": "user act outline\n",
            "chapters/vol-1-ch-1.md": "user chapter outline\n",
            "prompts/vol-1-ch-1.md": "user prompt\n",
            "drafts/vol-1-ch-1.md": "user draft\n",
            "texts/vol-1-ch-1.md": "user accepted text\n",
        }
        before = {}
        for rel, body in protected.items():
            before[rel] = digest(write(project, rel, body))

        write(project, ".claude/agents/reader.md", "tampered runtime\n")
        sync(project, "--check", expected=1)
        sync(project, "--skill-root", str(ROOT))
        for rel, expected_hash in before.items():
            assert digest(project / rel) == expected_hash, rel
        sync(project, "--check")

        incomplete = Path(tmp) / "incomplete-status"
        write(incomplete, "story.md", "# incomplete\n- skill_version: 5.2\n- runtime_profile: novel-pro-0.2\n")
        write(incomplete, ".agent/status.yaml", "migration:\n")
        sync(incomplete, "--skill-root", str(ROOT), "--check", expected=1)

    with tempfile.TemporaryDirectory(prefix="novel-pro-migration-") as tmp:
        old = Path(tmp) / "old-project"
        new = Path(tmp) / "new-project"
        write(
            old,
            "story.md",
            "# Old project\n- skill_version: 5.1\n- runtime_profile: pro-0.1\n",
        )
        write(old, "settings/genre-setting.md", "# old genre\n- genre_id: xianxia\n")
        write(old, "settings/world-setting.md", "old world\n")
        write(old, "volumes/volume-1.md", "old volume\n")
        write(old, "texts/vol-1-ch-1.md", "old text\n")
        write(old, ".agent/status.yaml", "cursor:\n  step: outline.chapters\n  volume: 2\n  act: 3\n  range: [1, 4]\n  paused_reason: \"\"\n")
        write(old, ".agent/order.yaml", "old order\n")
        write(old, ".claude/agents/novel-agent.md", "old runtime\n")
        write(old, "tools/sync_runtime.py", "old tool\n")
        write(old, "README.md", "manual file\n")
        old_story_before = digest(old / "story.md")

        sync(old, "--check", expected=1)
        migrate(old, new)
        migrated_story = (new / "story.md").read_text(encoding="utf-8")
        assert migrated_story.startswith(f"# {new.name}\n")
        assert "skill_version: 5.2" in migrated_story
        assert "runtime_profile: novel-pro-0.2" in migrated_story
        assert "- 题材: xianxia" in migrated_story
        assert "migrated genre" not in migrated_story
        assert (new / "CLAUDE.md").read_text(encoding="utf-8").startswith(f"# {new.name} - novel-pro v0.2\n")
        assert (new / "settings/world-setting.md").read_text(encoding="utf-8") == "old world\n"
        assert (new / "volumes/volume-1.md").read_text(encoding="utf-8") == "old volume\n"
        assert (new / "texts/vol-1-ch-1.md").read_text(encoding="utf-8") == "old text\n"
        assert digest(old / "story.md") == old_story_before
        report = (new / ".migration/report.json").read_text(encoding="utf-8")
        assert '"state": "review"' in report
        assert '"missing_project_files"' in report and ".agent/run-log.yaml" in report
        status = (new / ".agent/status.yaml").read_text(encoding="utf-8")
        assert "step: migration.review" in status
        assert "state: review" in status
        assert "resume_step: outline.chapters" in status
        sync(new, "--check", expected=1)

        run(sys.executable, "-B", str(MIGRATE), "finalize", str(new))
        status = (new / ".agent/status.yaml").read_text(encoding="utf-8")
        assert "step: outline.chapters" in status
        assert "state: complete" in status
        sync(new, "--check")

        deployed_source = Path(tmp) / "deployed-source"
        deployed_target = Path(tmp) / "deployed-target"
        write(
            deployed_source,
            "story.md",
            "# Another legacy project\n- skill_version: 5.0\n- runtime_profile: pro-0.1\n",
        )
        run(
            sys.executable,
            "-B",
            str(new / "tools/migrate.py"),
            str(deployed_source),
            str(deployed_target),
        )
        assert (deployed_target / ".migration/report.md").is_file()
        run(sys.executable, "-B", str(MIGRATE), "cleanup", str(new), "--confirm")
        assert not (old / ".claude/agents/novel-agent.md").exists()
        assert not (old / "tools/sync_runtime.py").exists()
        assert (old / "volumes/volume-1.md").is_file()
        assert (old / "README.md").is_file()
        status = (new / ".agent/status.yaml").read_text(encoding="utf-8")
        assert "cleanup: complete" in status

    with tempfile.TemporaryDirectory(prefix="novel-pro-story-yaml-") as tmp:
        old = Path(tmp) / "old-yaml"
        new = Path(tmp) / "new-project"
        write(old, "story.yaml", "title: legacy\nchapters:\n  - one\n")
        migrate(old, new)
        assert (new / ".migration/legacy/story.yaml").read_text(encoding="utf-8") == "title: legacy\nchapters:\n  - one\n"
        migrated_story = (new / "story.md").read_text(encoding="utf-8")
        assert migrated_story.startswith(f"# {new.name}\n")
        assert "runtime_profile: novel-pro-0.2" in migrated_story
        assert '"source_version": "unknown"' in (new / ".migration/report.json").read_text(encoding="utf-8")
        assert '"kind": "preserved-for-review"' in (new / ".migration/report.json").read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="novel-pro-init-boundary-") as tmp:
        existing = Path(tmp) / "existing"
        story = write(existing, "story.md", "# existing\n- skill_version: 5.2\n")
        before = digest(story)
        run(sys.executable, "-B", str(INIT), str(existing), "--genre", "1", expected=1)
        assert digest(story) == before
        assert not (existing / ".agent").exists()

        non_project = Path(tmp) / "non-project"
        marker = write(non_project, "README.md", "user content\n")
        marker_before = digest(marker)
        run(sys.executable, "-B", str(INIT), str(non_project), "--genre", "1", expected=1)
        assert digest(marker) == marker_before
        assert not (non_project / "story.md").exists()

    with tempfile.TemporaryDirectory(prefix="novel-pro-init-source-") as tmp:
        target = Path(tmp) / "project"
        env = os.environ.copy()
        env["NOVEL_SKILL_HOME"] = str(Path(tmp) / "missing-skill")
        run(sys.executable, "-B", str(INIT), str(target), "--genre", "1", expected=1, env=env)
        assert not target.exists()

    print("runtime safety smoke test passed")


if __name__ == "__main__":
    main()
