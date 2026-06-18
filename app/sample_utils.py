from __future__ import annotations

import re
from pathlib import Path


def parse_named_year_dir(name: str):
    m = re.match(r'^(?P<title>.+) \((?P<year>\d{4})\)$', name)
    if not m:
        return None
    return m.group('title'), int(m.group('year'))


def parent_sample(path: Path):
    parsed = parse_named_year_dir(path.parent.name)
    if not parsed:
        return None
    title, year = parsed
    return {'title': title, 'year': year}


def looks_normalized_episode(name: str):
    return bool(re.match(r'^.+\.\d{4}\.S\d{2}E\d{2,3}\.[^.]+$', name, re.I))


def find_primary_video_in_dir(path: Path):
    exts = {'.mkv', '.mp4', '.ts'}
    if not path.exists() or not path.is_dir():
        return None
    files = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in exts]
    files.sort()
    for f in files:
        if looks_normalized_episode(f.name) or re.match(r'^.+\.\d{4}\.[^.]+$', f.name, re.I):
            return f
    return files[0] if files else None
