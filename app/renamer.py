from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from .hard_rules import detect_kind, choose_title_and_year, extract_episode, matching_video_for_subtitle, choose_episode_target_from_siblings
from .tmdb import search_tmdb_title_id
from .parser import detect_language_suffix
from .utils import log_line

VIDEO_EXTS = {".mkv", ".mp4", ".ts", ".m2ts", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpg", ".mpeg", ".iso"}


def sanitize_output_title(title: str) -> str:
    # 新增规则：标题中移除标点/括号等符号，仅保留英文冒号(:)与中文冒号(：)
    s = re.sub(r'[^A-Za-z0-9\u4e00-\u9fff\s:：]+', ' ', title)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def categorized_root(media_root: Path, kind: str) -> Path:
    # 新增末尾规则：在原有命名规则执行后，再按类型归类到“电影/剧集”
    if kind == 'movie':
        return media_root / '电影'
    if kind == 'episode':
        return media_root / '剧集'
    return media_root


def with_tmdb_suffix(title_out: str, year: int | None, is_tv: bool) -> str:
    if not title_out or not year:
        return title_out
    tmdb_id = search_tmdb_title_id(title_out, year, is_tv=is_tv)
    if not tmdb_id:
        return f"{title_out} ({year})"
    return f"{title_out} ({year}) {{tmdb-{tmdb_id}}}"


def build_plan(path: Path, media_root: Path, config: dict, style=None):
    kind = detect_kind(path)
    ext = path.suffix.lower()

    if kind == 'movie':
        title, year = choose_title_and_year(path, media_root)
        if not title or not year:
            return None
        title_out = sanitize_output_title(title)
        if not title_out:
            return None
        target_dir = categorized_root(media_root, 'movie') / with_tmdb_suffix(title_out, year, is_tv=False)
        target = target_dir / f"{title_out}.{year}{ext}"
        if path == target:
            return None
        return path, target

    if kind == 'episode':
        title, year = choose_title_and_year(path, media_root)
        ep = extract_episode(path.stem)
        if title and year and ep:
            season, episode = ep
            title_out = sanitize_output_title(title)
            if not title_out:
                return None
            target_dir = categorized_root(media_root, 'episode') / with_tmdb_suffix(title_out, year, is_tv=True)
            target = target_dir / f"{title_out}.{year}.S{season:02d}E{episode:02d}{ext}"
            if path == target:
                return None
            return path, target

        sibling_target = choose_episode_target_from_siblings(path, media_root)
        if sibling_target:
            title = sibling_target['title']
            title_out = sanitize_output_title(title)
            if not title_out:
                return None
            year = sibling_target['year']
            season = sibling_target['season']
            episode = sibling_target['episode']
            if year:
                target_dir = categorized_root(media_root, 'episode') / with_tmdb_suffix(title_out, year, is_tv=True)
                target = target_dir / f"{title_out}.{year}.S{season:02d}E{episode:02d}{ext}"
            else:
                target_dir = categorized_root(media_root, 'episode') / title_out
                target = target_dir / f"{title_out}.S{season:02d}E{episode:02d}{ext}"
            if path == target:
                return None
            return path, target

        return None

    if kind == 'subtitle':
        video = matching_video_for_subtitle(path)
        lang_suffix = detect_language_suffix(path.stem)
        if video:
            video_plan = build_plan(video, media_root, config, style)
            if video_plan:
                _, video_target = video_plan
            else:
                video_target = video
            target_dir = video_target.parent
            base = video_target.stem
            target = target_dir / f"{base}{lang_suffix}{ext}"
            if path == target:
                return None
            return path, target
        title, year = choose_title_and_year(path, media_root)
        ep = extract_episode(path.stem)
        if ep and title and year:
            season, episode = ep
            title_out = sanitize_output_title(title)
            if not title_out:
                return None
            target_dir = categorized_root(media_root, 'episode') / with_tmdb_suffix(title_out, year, is_tv=True)
            base = f"{title_out}.{year}.S{season:02d}E{episode:02d}"
            target = target_dir / f"{base}{lang_suffix}{ext}"
            if path == target:
                return None
            return path, target
        if title and year:
            title_out = sanitize_output_title(title)
            if not title_out:
                return None
            target_dir = categorized_root(media_root, 'movie') / with_tmdb_suffix(title_out, year, is_tv=False)
            base = f"{title_out}.{year}"
            target = target_dir / f"{base}{lang_suffix}{ext}"
            if path == target:
                return None
            return path, target

    return None




def apply_plan(src: Path, dst: Path, dry_run: bool, log_file: str, media_roots: list[Path] | None = None):
    if src == dst:
        return 'skip'

    # 同名去重：仅对视频文件生效（字幕/其他类型不参与去重）
    src_ext = src.suffix.lower()
    if src_ext in VIDEO_EXTS:
        same_stem_exists = [
            p for p in dst.parent.glob(f"{dst.stem}.*")
            if p.is_file() and p != src and p.suffix.lower() in VIDEO_EXTS
        ]
    else:
        same_stem_exists = []

    if same_stem_exists:
        # 如果精确目标存在，优先与精确目标比较；否则与同名候选里最大的比较
        if dst.exists():
            compare_target = dst
        else:
            compare_target = max(same_stem_exists, key=lambda p: p.stat().st_size if p.exists() else -1)

        try:
            src_size = src.stat().st_size
            tgt_size = compare_target.stat().st_size
        except Exception:
            log_line(log_file, f'SKIP_EXISTS {src} -> {compare_target}')
            return 'exists'

        if src_size > tgt_size:
            if dry_run:
                log_line(log_file, f'DRY-RUN DEDUP_KEEP_LARGER replace {compare_target}({tgt_size}) with {src}({src_size}); old will be deleted')
                return 'dedup-dry-run-replace'
            try:
                compare_target.unlink()
            except Exception:
                log_line(log_file, f'FAILED_DELETE_OLD {compare_target}')
                return 'exists'
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            cleanup_empty_parents(src.parent, media_roots or [])
            log_line(log_file, f'DEDUP_KEEP_LARGER replaced {compare_target}({tgt_size}) with {src}({src_size}); old deleted')
            return 'dedup-replaced'

        if dry_run:
            log_line(log_file, f'DRY-RUN DEDUP_KEEP_LARGER keep {compare_target}({tgt_size}), delete smaller {src}({src_size})')
            return 'dedup-dry-run-delete'
        try:
            src.unlink()
        except Exception:
            log_line(log_file, f'FAILED_DELETE_SMALLER {src}')
            return 'exists'
        cleanup_empty_parents(src.parent, media_roots or [])
        log_line(log_file, f'DEDUP_KEEP_LARGER kept {compare_target}({tgt_size}), deleted smaller {src}({src_size})')
        return 'dedup-deleted'

    if dry_run:
        log_line(log_file, f'DRY-RUN {src} -> {dst}')
        return 'dry-run'
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    cleanup_empty_parents(src.parent, media_roots or [])
    log_line(log_file, f'MOVED {src} -> {dst}')
    return 'moved'


def cleanup_empty_parents(path: Path, media_roots: list[Path]):
    stop_paths = {p.resolve() for p in media_roots if p.exists()}
    current = path
    while True:
        try:
            resolved = current.resolve()
        except Exception:
            break
        if resolved in stop_paths:
            break
        try:
            if current.exists() and current.is_dir() and not any(current.iterdir()):
                os.rmdir(current)
                current = current.parent
                continue
        except Exception:
            break
        break
