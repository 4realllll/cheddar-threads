"""Публикует ответы из replies/outbox/*.json и переносит их в replies/sent/.

Формат файла: {"reply_to_id": "...", "text": "..."} или список таких объектов.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://graph.threads.net/v1.0"
ROOT = Path(__file__).resolve().parent.parent
OUTBOX = ROOT / "replies" / "outbox"
SENT = ROOT / "replies" / "sent"
MAX_LEN = 500


def post(path, params):
    req = urllib.request.Request(f"{API}{path}", data=urllib.parse.urlencode(params).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"POST {path} -> HTTP {e.code}: {e.read().decode(errors='replace')}") from None


def main():
    token = os.environ.get("THREADS_TOKEN", "").strip()
    if not token:
        print("Нет THREADS_TOKEN")
        return 1
    files = sorted(OUTBOX.glob("*.json"))
    if not files:
        print("Ответов в очереди нет.")
        return 0
    SENT.mkdir(parents=True, exist_ok=True)
    failed = False
    for f in files:
        items = json.loads(f.read_text(encoding="utf-8"))
        items = items if isinstance(items, list) else [items]
        for it in items:
            text = (it.get("text") or "").strip()
            if not text or not it.get("reply_to_id") or len(text) > MAX_LEN:
                it["result"] = "пропущен: пустой текст, нет reply_to_id или длиннее лимита"
                failed = True
                continue
            try:
                c = post("/me/threads", {"media_type": "TEXT", "text": text,
                                         "reply_to_id": it["reply_to_id"], "access_token": token})["id"]
                time.sleep(5)
                it["result"] = "ok"
                it["threads_id"] = post("/me/threads_publish", {"creation_id": c, "access_token": token})["id"]
                print(f"ответ на {it['reply_to_id']}: опубликован")
                time.sleep(3)
            except RuntimeError as e:
                it["result"] = f"ошибка: {e}"
                print(f"ответ на {it['reply_to_id']}: {e}")
                failed = True
        (SENT / f.name).write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        f.unlink()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
