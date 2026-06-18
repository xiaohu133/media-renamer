from __future__ import annotations

import os
import re
import json
import urllib.parse
import urllib.request


def _get(url: str, bearer: str):
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {bearer}',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _norm(s: str) -> str:
    s = (s or '').lower().replace('.', ' ').replace('_', ' ').strip()
    s = re.sub(r'\s+', ' ', s)
    return s


def _score_item(item: dict, query_title: str, year: int | None, is_tv: bool) -> tuple:
    q = _norm(query_title)
    orig = _norm(item.get('original_title') if not is_tv else item.get('original_name'))
    zh = (item.get('title') if not is_tv else item.get('name')) or ''
    date = (item.get('release_date') if not is_tv else item.get('first_air_date')) or ''
    item_year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None

    exact_orig = int(orig == q and q != '')
    contains_orig = int(q in orig or orig in q) if q and orig else 0
    year_match = int(year is not None and item_year == year)
    has_chinese_title = int(bool(re.search(r'[\u4e00-\u9fff]', zh)))
    popularity = float(item.get('popularity') or 0.0)
    votes = int(item.get('vote_count') or 0)

    return (exact_orig, contains_orig, year_match, has_chinese_title, popularity, votes)


def _search_tmdb_best(raw_title: str, year: int | None, is_tv: bool) -> dict | None:
    bearer = os.getenv('TMDB_BEARER_TOKEN', '').strip()
    if not bearer:
        return None
    title = raw_title.replace('.', ' ').replace('_', ' ').strip()
    title = re.sub(r'\s+', ' ', title)
    base = 'https://api.themoviedb.org/3/search/tv' if is_tv else 'https://api.themoviedb.org/3/search/movie'
    params = {'query': title, 'language': 'zh-CN'}
    if year:
        params['first_air_date_year' if is_tv else 'year'] = str(year)
    url = base + '?' + urllib.parse.urlencode(params)
    try:
        data = _get(url, bearer)
    except Exception:
        return None
    results = data.get('results') or []
    if not results:
        return None

    scored = sorted(results, key=lambda item: _score_item(item, title, year, is_tv), reverse=True)
    chinese_only = [item for item in scored if re.search(r'[\u4e00-\u9fff]', (item.get('name') if is_tv else item.get('title')) or '')]
    pool = chinese_only if chinese_only else scored
    return pool[0] if pool else None


def search_tmdb_title(raw_title: str, year: int | None, is_tv: bool) -> str | None:
    top = _search_tmdb_best(raw_title, year, is_tv)
    if not top:
        return None
    zh = top.get('name') if is_tv else top.get('title')
    return zh.strip() if isinstance(zh, str) and zh.strip() else None


def search_tmdb_title_id(raw_title: str, year: int | None, is_tv: bool) -> int | None:
    top = _search_tmdb_best(raw_title, year, is_tv)
    if not top:
        return None
    tmdb_id = top.get('id')
    return int(tmdb_id) if tmdb_id is not None else None
