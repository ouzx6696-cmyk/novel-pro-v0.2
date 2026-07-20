#!/usr/bin/env python3
"""Small stdlib helpers shared by source-side tools."""

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def is_relative_to(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except (ValueError, TypeError, OSError):
        return False


# These source-side helpers intentionally use a looser root threshold and take
# a story file path. The deployed sync tool keeps stricter local copies because
# project runtimes do not receive _common.py.
SKILL_MARKERS = ("SKILL.md", "skill.json", "agents", "skills", "knowledge", "tools")


def looks_like_skill_root(path, min_markers=4):
    path = Path(path)
    return path.is_dir() and sum((path / marker).exists() for marker in SKILL_MARKERS) >= min_markers


_VERSION_RE = re.compile(r"(?m)^\s*-?\s*skill_version\s*:\s*['\"]?([^'\"\s]+)")


def story_version(path):
    path = Path(path)
    if not path.is_file():
        return None
    match = _VERSION_RE.search(read_text(path))
    return match.group(1) if match else None
