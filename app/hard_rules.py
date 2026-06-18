from __future__ import annotations

import re
from pathlib import Path
from .tmdb import search_tmdb_title

VIDEO_EXTS = {'.mkv', '.mp4', '.ts', '.iso'}
SUB_EXTS = {'.srt', '.ass', '.ssa', '.sup', '.sub'}

def apply_fixed_title_rules(path: Path):
    return None


def has_cjk(text: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def normalize_dir_title(name: str) -> str:
    s = name.strip()
    s = re.sub(r'\([^)]*\)', '', s)
    s = re.sub(r'第[一二三四五六七八九十0-9]+季', '', s)
    s = re.sub(r'Season\s*\d+', '', s, flags=re.I)
    s = re.sub(r'简繁双语字幕|双语字幕|字幕组?', '', s)
    s = re.sub(r'4K|杜比世界|杜比视界|內封中文字幕|内封中文字幕|外挂简体字幕|简繁英字幕|全\d+集|单集\d+GB|\[.*?\]|［.*?］|（.*?GB）', '', s)
    s = re.sub(r'\bHEBREW\b|\bAMZN\b|\bATVP\b|\bWEB[- ]?DL\b|\bApple TV\+?\b|\bNF\b', '', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip(' -._')
    return s


def cleanup_raw_title(text: str) -> str:
    s = text.replace('.', ' ').replace('_', ' ')
    patterns = [
        r'\bS\d{1,2}E\d{2,3}\b', r'\bE\d{2,3}\b',
        r'\b2160p\b', r'\b1080p\b', r'\b720p\b', r'\b480p\b',
        r'\bWEB[- ]?DL\b', r'\bWEBRip\b', r'\bBluRay\b', r'\bRemux\b',
        r'\bAVC\b', r'\bHEVC\b', r'\bH\.?265\b', r'\bH\.?264\b',
        r'\bHDR\b', r'\bDV\b', r'\bAtmos\b', r'\bAAC\b', r'\bFLAC\b',
        r'\bDDP\s?5\.1\b', r'\bDTS[- ]?HD\b', r'\bMA\b', r'\bCHN\b',
        r'\bNF\b', r'\bQuickIO\b', r'\bHDBTHD\b', r'\bDolby Digital Plus 2\.0\b',
        r'\bHEBREW\b', r'\bREPACK\b', r'\biNTERNAL\b', r'\bMIXED\b',
        r'\b第\d+集\b', r'第[一二三四五六七八九十0-9]+季', r'4K', r'杜比世界', r'杜比视界',
        r'內封中文字幕', r'内封中文字幕', r'简繁英字幕', r'外挂简体字幕', r'全\d+集'
    ]
    for pat in patterns:
        s = re.sub(pat, ' ', s, flags=re.I)
    s = re.sub(r'\b\d+\s?fps\b', ' ', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip(' -._')
    return s


def ancestor_dirs(path: Path, media_root: Path):
    current = path.parent
    while current != media_root and media_root in current.parents:
        yield current
        current = current.parent


def extract_year(text: str):
    matches = re.findall(r'(19\d{2}|20\d{2})', text)
    return int(matches[-1]) if matches else None


def extract_last_year_match(text: str):
    matches = list(re.finditer(r'(19\d{2}|20\d{2})', text))
    return matches[-1] if matches else None


def extract_episode(stem: str):
    m = re.search(r'S(?P<s>\d{1,2})E(?P<e>\d{2,3})', stem, re.I)
    if not m:
        return None
    return int(m.group('s')), int(m.group('e'))


def detect_kind(path: Path):
    ext = path.suffix.lower()
    if ext in SUB_EXTS:
        return 'subtitle'
    if ext in VIDEO_EXTS:
        stem = path.stem
        if extract_episode(stem):
            return 'episode'
        if find_series_style_reference(path):
            return 'episode'
        return 'movie'
    return 'other'


def extract_title_part(stem: str, ep, year_match):
    if year_match:
        raw = stem[:year_match.start()]
        cleaned = cleanup_raw_title(raw)
        if cleaned:
            return cleaned
        matches = list(re.finditer(r'(19\d{2}|20\d{2})', stem))
        if len(matches) >= 2:
            fallback = ' '.join(m.group(1) for m in matches[:-1])
            cleaned_fallback = cleanup_raw_title(fallback)
            if cleaned_fallback:
                return cleaned_fallback
        return cleaned
    if ep:
        return cleanup_raw_title(re.split(r'S\d{1,2}E\d{2,3}', stem, flags=re.I)[0])
    return cleanup_raw_title(stem)


def extract_english_title(text: str) -> str:
    segments = [m.group(0).strip() for m in re.finditer(r"[A-Za-z][A-Za-z0-9'&:.-]*(?:\s+[A-Za-z0-9'&:.-]+)*", text)]
    if not segments:
        return ''

    non_english = re.sub(r"[A-Za-z0-9'&:.-]+", ' ', text)
    if has_cjk(non_english) and len(segments) >= 2:
        return segments[-1]

    english_parts = re.findall(r'[A-Za-z]+', text)
    return ' '.join(english_parts).strip()


def find_series_style_reference(path: Path, media_root: Path | None = None):
    current_dir = path.parent
    try:
        entries = sorted(current_dir.iterdir(), key=lambda p: p.name)
    except Exception:
        return None

    for cand in entries:
        if cand == path or not cand.is_file() or cand.suffix.lower() not in VIDEO_EXTS:
            continue
        cand_ep = extract_episode(cand.stem)
        if not cand_ep:
            continue

        cand_year_match = re.search(r'(19\d{2}|20\d{2})', cand.stem)
        cand_year = int(cand_year_match.group(1)) if cand_year_match else None
        title_part = extract_title_part(cand.stem, cand_ep, cand_year_match)
        if not title_part:
            continue

        title = None
        if has_cjk(title_part):
            title = title_part
        else:
            english_title = extract_english_title(title_part)
            if english_title:
                title = search_tmdb_title(english_title, cand_year, is_tv=True) or english_title

        if not title:
            continue

        return {
            'title': title,
            'year': cand_year,
            'season': cand_ep[0],
        }

    return None


def extract_episode_number_fallback(stem: str):
    numbers = re.findall(r'\d+', stem)
    if not numbers:
        return None
    return int(numbers[-1])


def choose_title_and_year(path: Path, media_root: Path):
    # 先走固定标题规则（用于兜底特殊命名）
    fixed = apply_fixed_title_rules(path)
    if fixed:
        return fixed

    # 只识别视频文件名；优先使用文件名中的年份作为边界；没有年份时改用 SxxExx 作为边界；此时年份取上级目录年份
    chosen_year = None
    dir_cjk_title = None
    for d in ancestor_dirs(path, media_root):
        year = extract_year(d.name)
        title = normalize_dir_title(d.name)
        if year and dir_cjk_title is None and has_cjk(title):
            dir_cjk_title = title
        if year and chosen_year is None:
            chosen_year = year

    stem = path.stem
    ep = extract_episode(stem)
    year_match = extract_last_year_match(stem)
    year = int(year_match.group(1)) if year_match else chosen_year
    title_part = extract_title_part(stem, ep, year_match)

    if year_match:
        english_title = extract_english_title(title_part)
        if english_title:
            tmdb_title = search_tmdb_title(english_title, year, is_tv=bool(ep))
            if tmdb_title:
                return tmdb_title, year
            if dir_cjk_title:
                return dir_cjk_title, year
            return english_title, year

    if has_cjk(title_part):
        return title_part, year

    english_title = extract_english_title(title_part)
    if english_title and ep:
        tmdb_title = search_tmdb_title(english_title, year, is_tv=True)
        if tmdb_title:
            return tmdb_title, year
        if dir_cjk_title:
            return dir_cjk_title, year
        return english_title, year

    if dir_cjk_title:
        return dir_cjk_title, year
    return title_part, year


def choose_episode_target_from_siblings(path: Path, media_root: Path):
    ref = find_series_style_reference(path, media_root)
    if not ref:
        return None

    episode = extract_episode_number_fallback(path.stem)
    if episode is None:
        return None

    title = ref['title']
    year = ref['year']
    if not title:
        return None

    season = ref.get('season') or 1

    return {
        'title': title,
        'year': year,
        'season': season,
        'episode': episode,
    }


def matching_video_for_subtitle(sub: Path):
    for ext in VIDEO_EXTS:
        cand = sub.with_suffix(ext)
        if cand.exists():
            return cand

    try:
        videos = [
            p for p in sub.parent.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTS
        ]
    except Exception:
        return None

    if len(videos) == 1:
        return videos[0]
    return None
