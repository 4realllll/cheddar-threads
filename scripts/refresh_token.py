"""Продлевает долгий токен Threads ещё на 60 дней.

Если Meta вернула новый токен (строка отличается) и задан секрет GH_PAT,
обновляет секрет THREADS_TOKEN через gh. Иначе печатает предупреждение и
завершается с ошибкой, чтобы GitHub прислал письмо.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

token = os.environ.get("THREADS_TOKEN", "").strip()
if not token:
    print("Нет секрета THREADS_TOKEN.")
    sys.exit(1)

url = "https://graph.threads.net/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "th_refresh_token", "access_token": token}
)
try:
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read())
except urllib.error.HTTPError as e:
    print(f"Продление не удалось: HTTP {e.code}: {e.read().decode(errors='replace')}")
    sys.exit(1)

new = data.get("access_token", "")
days = int(data.get("expires_in", 0)) // 86400
print(f"Токен продлён, действует ещё ~{days} дн.")

if new and new != token:
    pat = os.environ.get("GH_PAT", "").strip()
    if not pat:
        print("Meta выдала новую строку токена, но секрета GH_PAT нет — "
              "обновите THREADS_TOKEN вручную или добавьте GH_PAT.")
        sys.exit(1)
    subprocess.run(
        ["gh", "secret", "set", "THREADS_TOKEN", "--body", new,
         "--repo", os.environ["GITHUB_REPOSITORY"]],
        check=True, env={**os.environ, "GH_TOKEN": pat},
    )
    print("Секрет THREADS_TOKEN обновлён.")
