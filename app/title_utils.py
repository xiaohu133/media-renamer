from __future__ import annotations

import re

NOISE_PATTERNS = [
    r'简繁双语字幕',
    r'双语字幕',
    r'字幕组?',
    r'第二季',
    r'第[一二三四五六七八九十0-9]+季',
    r'合集',
    r'完结',
]


def contains_cjk(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def cleanup_parent_title(name: str) -> str:
    s = name
    s = re.sub(r'\([^)]*\)', '', s)
    for pat in NOISE_PATTERNS:
        s = re.sub(pat, '', s)
    s = re.sub(r'[._-]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(' -._')
    return s.strip()


def parent_cjk_title(name: str) -> str | None:
    cleaned = cleanup_parent_title(name)
    if contains_cjk(cleaned):
        return cleaned
    return None
