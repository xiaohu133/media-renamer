from __future__ import annotations

import re
from pathlib import Path
from collections import Counter

MOVIE_RE = re.compile(r'^(?P<title>.+)\.(?P<year>\d{4})\.[^.]+$', re.I)
EP_RE = re.compile(r'^(?P<title>.+)\.(?P<year>\d{4})\.S(?P<season>\d{2})E(?P<episode>\d{2,3})\.[^.]+$', re.I)


class StyleProfile:
    def __init__(self):
        self.episode_digits_global = 2
        self.series_digits = {}
        self.series_dirs = {}


def detect_styles(media_root: Path, config: dict) -> StyleProfile:
    profile = StyleProfile()
    ext_ok = set(config['extensions']['video']) | set(config['extensions']['disc']) | set(config['extensions']['subtitle'])
    digits_counter = Counter()

    for p in media_root.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in ext_ok:
            continue
        m = EP_RE.match(p.name)
        if m:
            title = m.group('title')
            digits = len(m.group('episode'))
            digits_counter[digits] += 1
            profile.series_digits[title] = digits
            profile.series_dirs[title] = p.parent.name

    if digits_counter:
        profile.episode_digits_global = digits_counter.most_common(1)[0][0]
    return profile


def infer_series_dir(title: str, year: int, profile: StyleProfile) -> str:
    return profile.series_dirs.get(title, f'{title} ({year})')


def infer_episode_digits(title: str, profile: StyleProfile) -> int:
    return profile.series_digits.get(title, profile.episode_digits_global)
