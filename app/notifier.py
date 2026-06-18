from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


def _escape_html(text: str) -> str:
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))


def notify_rename_result(config: dict, result: str, src: Path, dst: Path) -> None:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return

    action_map = {
        'moved': '已完成重命名',
        'dedup-replaced': '已完成替换去重',
        'dedup-deleted': '已完成重复清理',
    }
    action = action_map.get(result, result)
    text = (
        f'✅ <b>media-renamer {action}</b>\n'
        f'<b>来源:</b> <code>{_escape_html(str(src))}</code>\n'
        f'<b>结果:</b> <code>{_escape_html(str(dst))}</code>'
    )

    payload = json.dumps({
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }).encode('utf-8')

    req = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except Exception:
        pass
