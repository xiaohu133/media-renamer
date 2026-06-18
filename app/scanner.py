from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Iterable


def iter_recent_files(root: str, recent_hours: int, config: dict):
    cutoff = datetime.now().timestamp() - recent_hours * 3600
    yield from iter_candidate_files(root, config, cutoff=cutoff)


def iter_candidate_files(root: str, config: dict, cutoff: float | None = None) -> Iterable[Path]:
    ignore_dirs = set(config.get('ignore_dirs', [])) | {'.dedup_removed'}
    all_exts = set(config['extensions']['video']) | set(config['extensions']['subtitle']) | set(config['extensions']['disc'])

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for filename in filenames:
            p = Path(dirpath) / filename
            try:
                if p.suffix.lower() not in all_exts:
                    continue
                st = p.stat()
                if cutoff is not None and st.st_mtime < cutoff:
                    continue
                yield p
            except FileNotFoundError:
                continue
            except OSError:
                continue
