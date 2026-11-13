"""Рисует картинку для поста в Threads в стиле Чеддера.

Пример:
  python3 scripts/make_card.py --title "Ученик прислал ДЗ в 23:47" \
      --subtitle "Отвечаете сразу или утром?" --pose assets/poses/avatar-circle.png \
      --out posts/queue/2026-11-20.png

Картинка 1080×1350: жёлтый фон, тёмно-синий текст сверху, Чеддер снизу.
Позы с прозрачным фоном ставятся как есть; файлы с «-circle» в имени
обрезаются по кругу.
"""
import argparse
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1350
YELLOW = (253, 193, 54)
HOLE = (254, 212, 106)
NAVY = (30, 42, 74)
BOLD = ROOT / "assets/fonts/Inter-Bold.otf"
MEDIUM = ROOT / "assets/fonts/Inter-Medium.otf"


def glue(text):
    """Неразрывный пробел после коротких слов («в 7 утра» не рвётся)."""
    return re.sub(r"(?<![^\s«(])(\S{1,2}) (?=\S)", "\\1\u00a0", text)


def wrap(draw, text, font, width):
    lines = []
    for para in glue(text).split("\n"):
        line = ""
        for word in [w for w in para.split(" ") if w]:
            test = f"{line} {word}".strip()
            if draw.textlength(test, font=font) <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


def fit_text(draw, text, path, max_size, min_size, width, max_lines):
    size = max_size
    while size >= min_size:
        font = ImageFont.truetype(str(path), size)
        lines = wrap(draw, text, font, width)
        if len(lines) <= max_lines:
            return font, lines
        size -= 4
    font = ImageFont.truetype(str(path), min_size)
    return font, wrap(draw, text, font, width)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--pose", default=str(ROOT / "assets/poses/avatar-circle.png"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()

    img = Image.new("RGB", (W, H), YELLOW)
    d = ImageDraw.Draw(img)

    rnd = random.Random(a.seed if a.seed is not None else a.title)
    for x, y in [(-40, 260), (W + 30, 520), (60, H - 120), (W - 90, 90), (W - 40, H - 330)]:
        r = rnd.randint(45, 95)
        d.ellipse((x - r, y - r, x + r, y + r), fill=HOLE)

    margin = 90
    y = 110
    tfont, tlines = fit_text(d, a.title, BOLD, 84, 52, W - 2 * margin, 4)
    for line in tlines:
        d.text((margin, y), line, font=tfont, fill=NAVY)
        y += int(tfont.size * 1.18)
    if a.subtitle:
        y += 24
        sfont, slines = fit_text(d, a.subtitle, MEDIUM, 48, 36, W - 2 * margin, 3)
        for line in slines:
            d.text((margin, y), line, font=sfont, fill=NAVY)
            y += int(sfont.size * 1.3)

    pose = Image.open(a.pose)
    space = H - y - 40
    size = max(420, min(760, space))
    if "-circle" in Path(a.pose).stem:
        pose = pose.convert("RGB").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        inset = int(size * 0.03)
        ImageDraw.Draw(mask).ellipse((inset, inset, size - inset, size - inset), fill=255)
        img.paste(pose, ((W - size) // 2, H - size - 30), mask)
    else:
        pose = pose.convert("RGBA")
        pose.thumbnail((W - 120, size), Image.LANCZOS)
        img.paste(pose, ((W - pose.width) // 2, H - pose.height - 30), pose)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(out)


if __name__ == "__main__":
    main()
