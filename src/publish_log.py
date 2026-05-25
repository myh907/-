"""发布记录：追加写入 publish_log.jsonl，每行一条 JSON。"""

import json
import os
from datetime import datetime, timezone


LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "publish_log.jsonl")


def write(topic: str, title: str, media_id: str, publish_id: str, status: str) -> None:
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "title": title,
        "media_id": media_id,
        "publish_id": publish_id,
        "status": status,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_recent(n: int = 10) -> list[dict]:
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    return [json.loads(l) for l in lines[-n:]]
