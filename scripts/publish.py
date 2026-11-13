"""Публикует посты из posts/queue/ в Threads и переносит их в posts/published/.

Запускается из GitHub Actions. Токен берётся из переменной окружения THREADS_TOKEN.
Только стандартная библиотека Python.
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
QUEUE = ROOT / "posts" / "queue"
PUBLISHED = ROOT / "posts" / "published"
MAX_LEN = 500  # лимит Threads на текст поста


def call(method: str, path: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {body}") from None


def publish(text: str, token: str) -> str:
    container = call("POST", "/me/threads", {
        "media_type": "TEXT", "text": text, "access_token": token,
    })["id"]
    time.sleep(5)
    return call("POST", "/me/threads_publish", {
        "creation_id": container, "access_token": token,
    })["id"]


def main() -> int:
    token = os.environ.get("THREADS_TOKEN", "").strip()
    if not token:
        print("Нет секрета THREADS_TOKEN в настройках репозитория.")
        return 1

    files = sorted(p for p in QUEUE.glob("*.txt"))
    if not files:
        print("Очередь пуста, публиковать нечего.")
        return 0

    me = call("GET", "/me", {"fields": "id,username", "access_token": token})
    print(f"Аккаунт: @{me.get('username')}")

    PUBLISHED.mkdir(parents=True, exist_ok=True)
    failed = False
    for f in files:
        text = f.read_text(encoding="utf-8").strip()
        if not text:
            print(f"{f.name}: пустой файл, пропускаю")
            f.unlink()
            continue
        if len(text) > MAX_LEN:
            print(f"{f.name}: {len(text)} символов, больше лимита {MAX_LEN}, пропускаю")
            failed = True
            continue
        try:
            post_id = publish(text, token)
        except RuntimeError as e:
            print(f"{f.name}: ошибка публикации: {e}")
            failed = True
            continue
        out = PUBLISHED / f.name
        out.write_text(f"{text}\n\n---\nthreads_id: {post_id}\n", encoding="utf-8")
        f.unlink()
        print(f"{f.name}: опубликован, id {post_id}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
