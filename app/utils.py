from __future__ import annotations

from pathlib import Path
from datetime import datetime


def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def log_line(log_file: str | Path, message: str) -> None:
    ensure_parent(log_file)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f'[{ts}] {message}\n')
