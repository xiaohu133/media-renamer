from __future__ import annotations

import re
from pathlib import Path

VIDEO_EXTS = {'.mkv', '.mp4', '.ts'}
SUB_EXTS = {'.srt', '.ass', '.ssa', '.sup', '.sub'}
DISC_EXTS = {'.iso'}

NAMED_YEAR_DIR = re.compile(r'^(?P<title>.+) \((?P<year>\d{4})\)$')
EP_IN_NAME = re.compile(r'S(?P<season>\d{1,2})E(?P<episode>\d{2,3})', re.I)
MOVIE_IN_NAME = re.compile(r'^(?P<title>.+?)[. _-]*\(?(?P<year>19\d{2}|20\d{2}|21\d{2})\)?', re.I)


def parse_named_year_dir(name: str):
    m = NAMED_YEAR_DIR.match(name)
    if not m:
        return None
    return {'title': m.group('title'), 'year': int(m.group('year'))}


def classify(path: Path):
    ext = path.suffix.lower()
    if ext in DISC_EXTS:
        return 'disc'
    if ext in SUB_EXTS:
        return 'subtitle'
    if ext in VIDEO_EXTS:
        stem = path.stem
        if EP_IN_NAME.search(stem):
            return 'episode'
        return 'movie'
    return 'other'


def ancestor_named_year(path: Path, media_root: Path):
    current = path.parent
    while current != media_root and media_root in current.parents:
        parsed = parse_named_year_dir(current.name)
        if parsed:
            return current, parsed
        current = current.parent
    return None, None


def season_subdir_between(named_dir: Path | None, file_parent: Path):
    if not named_dir:
        return None
    rel = file_parent.relative_to(named_dir)
    if len(rel.parts) >= 1:
        first = rel.parts[0]
        if re.match(r'^Season\s+\d+$', first, re.I):
            return first
    return None


def extract_ep(stem: str):
    m = EP_IN_NAME.search(stem)
    if not m:
        return None
    return {'season': int(m.group('season')), 'episode': int(m.group('episode')), 'digits': len(m.group('episode'))}


def same_type_samples(media_root: Path, kind: str):
    for p in media_root.rglob('*'):
        if p.is_file() and classify(p) == kind:
            yield p


def choose_sample(path: Path, media_root: Path, kind: str):
    named_dir, parsed = ancestor_named_year(path, media_root)
    if named_dir:
        for p in named_dir.rglob('*'):
            if p.is_file() and classify(p) == kind and p != path:
                return p, named_dir, parsed
    for p in same_type_samples(media_root, kind):
        if p != path:
            return p, None, None
    return None, named_dir, parsed
