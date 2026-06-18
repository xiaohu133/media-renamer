from __future__ import annotations

import json
from pathlib import Path


def load_state(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {"handled": {}, "planned": {}}
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        data.setdefault('handled', {})
        data.setdefault('planned', {})
        return data
    except Exception:
        return {"handled": {}, "planned": {}}


def save_state(path: str | Path, state: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
