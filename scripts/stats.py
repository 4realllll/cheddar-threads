"""Собирает статистику Threads: по каждому опубликованному посту и по аккаунту.

Пишет stats/posts.json (сырые числа) и stats/latest.md (таблица для чтения).
Нужно разрешение threads_manage_insights у токена.
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
OUT = ROOT / "stats"
POST_METRICS = "views,likes,replies,reposts,quotes,shares"


def get(path, params):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GET {path} -> HTTP {e.code}: {e.read().decode(errors='replace')}") from None


def values(resp):
    out = {}
    for m in resp.get("data", []):
        if "values" in m and m["values"]:
            out[m["name"]] = m["values"][-1].get("value", 0)
        elif "total_value" in m:
            out[m["name"]] = m["total_value"].get("value", 0)
    return out


def main():
    token = os.environ.get("THREADS_TOKEN", "").strip()
    if not token:
        print("Нет THREADS_TOKEN")
        return 1

    posts = []
    for f in sorted(PUBLISHED.glob("*.txt")):
        raw = f.read_text(encoding="utf-8")
        m = re.search(r"threads_id:\s*(\d+)", raw)
        if not m:
            continue
        text = raw.split("\n---\n")[0].strip()
        posts.append({
            "date": f.stem, "id": m.group(1), "text": text,
            "image": "image:" in raw, "chars": len(text),
        })

    errors = []
    for p in posts:
        try:
            p.update(values(get(f"/{p['id']}/insights", {"metric": POST_METRICS, "access_token": token})))
        except RuntimeError as e:
            errors.append(f"{p['date']}: {e}")

    account = {}
    try:
        account = values(get("/me/threads_insights", {
            "metric": "views,likes,replies,reposts,quotes,followers_count",
            "access_token": token,
        }))
    except RuntimeError as e:
        errors.append(f"аккаунт: {e}")

    OUT.mkdir(exist_ok=True)
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).strftime("%Y-%m-%d %H:%M МСК")
    (OUT / "posts.json").write_text(json.dumps(
        {"updated": now, "account": account, "posts": posts, "errors": errors},
        ensure_ascii=False, indent=1), encoding="utf-8")

    def eng(p):
        return sum(p.get(k, 0) or 0 for k in ("likes", "replies", "reposts", "quotes", "shares"))

    lines = [f"# Статистика Threads @cheddar_check", f"Обновлено: {now}", ""]
    if account:
        lines.append("Аккаунт (за последний период API): " + ", ".join(f"{k}: {v}" for k, v in account.items()))
        lines.append("")
    lines.append("| Дата | Просм. | Лайки | Ответы | Репосты | Цит. | Вовлеч. % | Карт. | Начало поста |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for p in reversed(posts):
        v = p.get("views", 0) or 0
        rate = f"{100 * eng(p) / v:.1f}" if v else "—"
        start = p["text"].replace("\n", " ")[:60].replace("|", "/")
        lines.append(f"| {p['date']} | {v} | {p.get('likes', 0)} | {p.get('replies', 0)} | "
                     f"{p.get('reposts', 0)} | {p.get('quotes', 0)} | {rate} | "
                     f"{'да' if p['image'] else ''} | {start}… |")
    if errors:
        lines += ["", "Ошибки:"] + [f"- {e}" for e in errors]
    (OUT / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if errors and not any("views" in p for p in posts) else 0


if __name__ == "__main__":
    sys.exit(main())
