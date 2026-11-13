# cheddar-threads

Автопостинг Чеддера в Threads (@cheddar_check).

- Облачная задача Claude «Threads Чеддер» 2–3 раза в день кладёт пост в `posts/queue/ГГГГ-ММ-ДД-N.txt` (N — слот: 1 утро, 2 день, 3 вечер) и делает push.
- GitHub Actions (`publish.yml`) публикует всё из очереди через Threads API и переносит файлы в `posts/published/` с id поста.
- `refresh-token.yml` 1-го и 15-го числа продлевает токен на 60 дней.

Секреты репозитория (Settings → Secrets and variables → Actions):
- `THREADS_TOKEN` — долгий токен Threads (обязательно).
- `GH_PAT` — необязательно: fine-grained токен GitHub с правом *Secrets: read and write* на этот репозиторий. Нужен, только если при продлении Meta выдаст новую строку токена.

Картинки: положите рядом с постом `ГГГГ-ММ-ДД.png` (рисует `scripts/make_card.py`, позы Чеддера — в `assets/poses/`). Картинку Threads забирает по публичной ссылке, поэтому репозиторий должен быть **публичным** (секретов в нём нет, токен лежит в Secrets). Если репозиторий приватный, пост выйдет без картинки.

Опубликовать вручную: положите `.txt` в `posts/queue/` (до 500 символов) или запустите workflow «Публикация в Threads» кнопкой Run workflow.
Ошибки: GitHub присылает письмо, если запуск упал.
