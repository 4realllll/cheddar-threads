"""Собирает комментарии под постами за последние 21 день.

Пишет replies/conversations.json (все ветки) и replies/inbox.md — комментарии
других людей, на которые аккаунт ещё не ответил. Нужно разрешение
threads_read_replies у токена.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://graph.threads.net/v1.0"
ROOT = Path(__file__).resolve().parent.parent
PUBLISHED = ROOT / "posts" / "published"
OUT = ROOT / "replies"
FIELDS = "id,text,username,timestamp,replied_to,root_post,media_type,hide_status"
DAYS = 21


def get(path, params):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GET {path} -> HTTP {e.code}: {e.read().decode(errors='replace')}") from None


def conversation(post_id, token):
    items, params = [], {"fields": FIELDS, "reverse": "false", "access_token": token}
    path = f"/{post_id}/conversation"
    while True:
        resp = get(path, params)
        items += resp.get("data", [])
        nxt = resp.get("paging", {}).get("cursors", {}).get("after")
        if not nxt or not resp.get("paging", {}).get("next"):
            return items
        params["after"] = nxt


def main():
    token = os.environ.get("THREADS_TOKEN", "").strip()
    if not token:
        print("Нет THREADS_TOKEN")
        return 1
    me = get("/me", {"fields": "username", "access_token": token})["username"]
    cutoff = (dt.date.today() - dt.timedelta(days=DAYS)).isoformat()

    threads = []
    for f in sorted(PUBLISHED.glob("*.txt")):
        if f.stem < cutoff:
            continue
        raw = f.read_text(encoding="utf-8")
        m = re.search(r"threads_id:\s*(\d+)", raw)
        if not m:
            continue
        post_id = m.group(1)
        replies = conversation(post_id, token)
        threads.append({"date": f.stem, "post_id": post_id,
                        "post_text": raw.split("\n---\n")[0].strip(), "replies": replies})

    answered = {r.get("replied_to", {}).get("id")
                for t in threads for r in t["replies"] if r.get("username") == me}
    by_id = {r["id"]: r for t in threads for r in t["replies"]}
    skip_file = OUT / "left-for-nikita.txt"
    skipped = set(skip_file.read_text().split()) if skip_file.exists() else set()

    OUT.mkdir(exist_ok=True)
    (OUT / "conversations.json").write_text(
        json.dumps({"me": me, "threads": threads}, ensure_ascii=False, indent=1), encoding="utf-8")

    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).strftime("%Y-%m-%d %H:%M МСК")
    lines = ["# Комментарии без ответа", ""]  # без времени: файл меняется только при новых комментариях
    pending = 0
    for t in threads:
        todo = [r for r in t["replies"]
                if r.get("username") != me and r["id"] not in answered and r["id"] not in skipped
                and r.get("hide_status") in (None, "NOT_HUSHED", "UNHUSHED")]
        if not todo:
            continue
        lines += [f"## Пост {t['date']} (id {t['post_id']})", "", "> " + t["post_text"].replace("\n", "\n> "), ""]
        for r in todo:
            parent = by_id.get(r.get("replied_to", {}).get("id"))
            ctx = f" (в ответ на @{parent['username']}: «{(parent.get('text') or '')[:120]}»)" if parent else ""
            lines.append(f"- reply_to_id `{r['id']}` · @{r.get('username')} · {r.get('timestamp', '')[:16]}{ctx}")
            lines.append(f"  «{(r.get('text') or '[без текста]').strip()}»")
            pending += 1
        lines.append("")
    if not pending:
        lines.append("Новых комментариев нет.")
    (OUT / "inbox.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
