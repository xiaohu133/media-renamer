from __future__ import annotations

from pathlib import Path
import yaml


def load_config(path: str | Path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    mapping_path = Path(path).with_name('title_mappings.yaml')
    if mapping_path.exists():
        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping_cfg = yaml.safe_load(f) or {}
        cfg['title_mappings'] = mapping_cfg.get('title_mappings', {})
    else:
        cfg['title_mappings'] = {}
    return cfg
