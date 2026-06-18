"""FastAPI Web UI for media-renamer"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Media Renamer Web UI")

CONFIG_PATH = Path("/app/config/config.yaml")
TITLE_MAPPINGS_PATH = Path("/app/config/title_mappings.yaml")
STATE_PATH = Path("/app/data/state.json")
LOG_PATH = Path("/app/data/logs/actions.log")


class ConfigUpdate(BaseModel):
    media_roots: Optional[list[str]] = None
    recent_hours_default: Optional[int] = None
    extensions: Optional[dict] = None
    naming: Optional[dict] = None
    ignore_dirs: Optional[list[str]] = None


class TitleMappingsUpdate(BaseModel):
    title_mappings: dict[str, str]


class ScanRequest(BaseModel):
    dry_run: bool = True
    recent_hours: Optional[int] = None
    limit: int = 0


def _load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _load_title_mappings() -> dict:
    if not TITLE_MAPPINGS_PATH.exists():
        return {}
    with open(TITLE_MAPPINGS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("title_mappings", {})


def _save_title_mappings(mappings: dict):
    with open(TITLE_MAPPINGS_PATH, "w", encoding="utf-8") as f:
        yaml.dump({"title_mappings": mappings}, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


@app.get("/api/status")
def api_status():
    config = _load_config()
    state = {}
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    log_lines = 0
    if LOG_PATH.exists():
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            log_lines = sum(1 for _ in f)
    return {
        "media_roots": config.get("media_roots", []),
        "handled_count": len(state.get("handled", {})),
        "planned_count": len(state.get("planned", {})),
        "log_lines": log_lines,
    }


@app.get("/api/config")
def api_get_config():
    return _load_config()


@app.put("/api/config")
def api_update_config(body: ConfigUpdate):
    cfg = _load_config()
    if body.media_roots is not None:
        cfg["media_roots"] = body.media_roots
    if body.recent_hours_default is not None:
        cfg["recent_hours_default"] = body.recent_hours_default
    if body.extensions is not None:
        cfg["extensions"] = body.extensions
    if body.naming is not None:
        cfg["naming"] = body.naming
    if body.ignore_dirs is not None:
        cfg["ignore_dirs"] = body.ignore_dirs
    _save_config(cfg)
    return {"ok": True, "config": cfg}


@app.get("/api/title-mappings")
def api_get_title_mappings():
    return {"title_mappings": _load_title_mappings()}


@app.put("/api/title-mappings")
def api_update_title_mappings(body: TitleMappingsUpdate):
    _save_title_mappings(body.title_mappings)
    return {"ok": True, "title_mappings": body.title_mappings}


@app.get("/api/logs")
def api_get_logs(tail: int = 100, search: Optional[str] = None):
    if not LOG_PATH.exists():
        return {"lines": [], "total": 0}
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
    if search:
        all_lines = [line for line in all_lines if search in line]
    total = len(all_lines)
    lines = all_lines[-tail:]
    lines.reverse()
    return {"lines": [line.rstrip() for line in lines], "total": total}


@app.post("/api/plan")
def api_run_plan(req: ScanRequest):
    cmd = ["python", "-m", "app.main", "plan", "--config", str(CONFIG_PATH)]
    if req.recent_hours:
        cmd += ["--recent-hours", str(req.recent_hours)]
    if req.limit:
        cmd += ["--limit", str(req.limit)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd="/app")
        output_lines = [x for x in result.stdout.strip().splitlines() if x]
        return {"plans": output_lines, "stderr": result.stderr.strip()}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Plan execution timed out")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/scan")
def api_run_scan(req: ScanRequest):
    cmd = ["python", "-m", "app.main", "scan", "--config", str(CONFIG_PATH)]
    if not req.dry_run:
        cmd += ["--apply"]
    if req.recent_hours:
        cmd += ["--recent-hours", str(req.recent_hours)]
    if req.limit:
        cmd += ["--limit", str(req.limit)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd="/app")
        output_lines = [x for x in result.stdout.strip().splitlines() if x]
        return {"results": output_lines, "stderr": result.stderr.strip()}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Scan execution timed out")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/api/state")
def api_clear_state():
    STATE_PATH.write_text(
        json.dumps({"handled": {}, "planned": {}}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def serve_index():
    html_path = Path(__file__).parent / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")
