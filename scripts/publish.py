"""Публикует посты из posts/queue/ в Threads и переносит их в posts/published/.

Пост — файл ГГГГ-ММ-ДД.txt. Если рядом лежит ГГГГ-ММ-ДД.png, пост выходит
с картинкой (картинка берётся по публичной ссылке raw.githubusercontent.com,
поэтому репозиторий должен быть публичным; иначе пост выйдет без картинки).

Запускается из GitHub Actions. Токен — переменная окружения THREADS_TOKEN.
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


def public_url(rel_path: str) -> str | None:
    repo = os.environ.get("GITHUB_REPOSITORY")
    sha = os.environ.get("GITHUB_SHA")
    if not repo or not sha:
        return None
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{rel_path}"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return url if resp.status == 200 else None
    except urllib.error.URLError:
        return None


def wait_ready(container: str, token: str) -> None:
    for _ in range(20):
        st = call("GET", f"/{container}", {"fields": "status,error_message", "access_token": token})
        status = st.get("status")
        if status in (None, "FINISHED", "PUBLISHED"):
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"контейнер {status}: {st.get('error_message')}")
        time.sleep(3)
    raise RuntimeError("контейнер не успел обработаться")


def publish(text: str, token: str, image_url: str | None) -> str:
    params = {"text": text, "access_token": token}
    if image_url:
        params.update(media_type="IMAGE", image_url=image_url)
    else:
        params.update(media_type="TEXT")
    container = call("POST", "/me/threads", params)["id"]
    time.sleep(5)
    wait_ready(container, token)
    return call("POST", "/me/threads_publish", {
        "creation_id": container, "access_token": token,
    })["id"]


def main() -> int:
    token = os.environ.get("THREADS_TOKEN", "").strip()
    if not token:
        print("Нет секрета THREADS_TOKEN в настройках репозитория.")
        return 1

    files = sorted(QUEUE.glob("*.txt"))
    if not files:
        print("Очередь пуста, публиковать нечего.")
        return 0

    me = call("GET", "/me", {"fields": "id,username", "access_token": token})
    print(f"Аккаунт: @{me.get('username')}")

    PUBLISHED.mkdir(parents=True, exist_ok=True)
    failed = False
    for f in files:
        text = f.read_text(encoding="utf-8").strip()
        png = f.with_suffix(".png")
        if not text:
            print(f"{f.name}: пустой файл, пропускаю")
            f.unlink()
            continue
        if len(text) > MAX_LEN:
            print(f"{f.name}: {len(text)} символов, больше лимита {MAX_LEN}, пропускаю")
            failed = True
            continue

        image_url = None
        if png.exists():
            image_url = public_url(png.relative_to(ROOT).as_posix())
            if not image_url:
                print(f"{png.name}: картинка недоступна по публичной ссылке "
                      "(репозиторий приватный?) — публикую без неё")

        try:
            post_id = publish(text, token, image_url)
        except RuntimeError as e:
            print(f"{f.name}: ошибка публикации: {e}")
            failed = True
            continue
        note = f"\nimage: {png.name}" if image_url else ""
        (PUBLISHED / f.name).write_text(
            f"{text}\n\n---\nthreads_id: {post_id}{note}\n", encoding="utf-8")
        f.unlink()
        if png.exists():
            png.rename(PUBLISHED / png.name)
        print(f"{f.name}: опубликован{' с картинкой' if image_url else ''}, id {post_id}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
