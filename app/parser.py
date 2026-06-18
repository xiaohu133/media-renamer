from __future__ import annotations

import re

QUALITY_TOKENS = {
    '2160p', '1080p', '720p', '480p', 'bluray', 'blu-ray', 'bdrip', 'web-dl', 'webrip',
    'hdr', 'hdr10', 'dovi', 'dv', 'hevc', 'x265', 'x264', 'dts', 'aac', 'ddp', 'atmos',
    'remux', 'uhd', 'ger', 'chs', 'cht', 'monument', 'ma', '5', '5.1'
}


def is_video_or_disc(ext: str, config: dict) -> bool:
    exts = set(config['extensions']['video']) | set(config['extensions']['disc'])
    return ext.lower() in exts


def is_subtitle(ext: str, config: dict) -> bool:
    return ext.lower() in set(config['extensions']['subtitle'])


def already_normalized(name: str) -> bool:
    return bool(re.match(r'^.+\.\d{4}(\.S\d{2}E\d{2,3})?\.[^.]+$', name, re.I))


def parse_episode(name: str):
    patterns = [
        r'^(?P<title>.+?)[. _-]+(?P<year>\d{4})[. _-]+S(?P<season>\d{1,2})E(?P<episode>\d{1,3})(?:[. _-].*)?$',
        r'^(?P<title>.+?)[. _-]+S(?P<season>\d{1,2})E(?P<episode>\d{1,3})(?:[. _-].*)?$',
    ]
    for pat in patterns:
        m = re.match(pat, name, re.I)
        if not m:
            continue
        return {
            'kind': 'episode',
            'title': cleanup_title(m.group('title')),
            'year': int(m.group('year')) if m.groupdict().get('year') else None,
            'season': int(m.group('season')),
            'episode': int(m.group('episode')),
        }
    return None


def parse_movieish(name: str):
    m = re.search(r'(?P<title>.*?)[. _-]+(?P<year>19\d{2}|20\d{2}|21\d{2})(?:$|[. _-]+)', name)
    if not m:
        return None
    return {
        'kind': 'movie',
        'title': cleanup_title(m.group('title')),
        'year': int(m.group('year')),
    }


def cleanup_title(raw: str) -> str:
    s = raw.replace('.', ' ').replace('_', ' ').strip()
    parts = [p for p in re.split(r'\s+', s) if p]
    kept = []
    for p in parts:
        if p.lower() in QUALITY_TOKENS:
            continue
        kept.append(p)
    return ' '.join(kept).strip(' -._')


def detect_language_suffix(stem: str) -> str:
    lower = stem.lower()
    for token in ['.zh-cn', '.zh-tw', '.zh', '.chs', '.cht', '.cn', '.sc', '.tc', '.eng', '.en']:
        if lower.endswith(token):
            return token
    return ''


def extract_year_from_text(text: str):
    m = re.search(r'\((\d{4})\)', text)
    return int(m.group(1)) if m else None
