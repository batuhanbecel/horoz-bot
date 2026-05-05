from __future__ import annotations

import io
import os

from PIL import Image, ImageDraw, ImageFont

# ── Discord dark-theme renk paleti ───────────────────────────────────────────
_BG     = (43,  45,  49)
_CARD   = (56,  58,  64)
_WHITE  = (219, 222, 225)
_GRAY   = (181, 186, 193)
_GREEN  = ( 57, 167,  82)
_YELLOW = (250, 168,  26)
_RED    = (224,  60,  60)
_BAR_BG = ( 61,  63,  69)
_ACCENT = (180,  30,  30)

W, H = 800, 295


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in [
        f"C:/Windows/Fonts/{'arialbd' if bold else 'arial'}.ttf",
        f"C:/Windows/Fonts/{'calibrib' if bold else 'calibri'}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf".format("-Bold" if bold else ""),
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _paste_avatar(img: Image.Image, av_bytes: bytes, x: int, y: int, size: int) -> None:
    try:
        av   = Image.open(io.BytesIO(av_bytes)).convert("RGBA").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        img.paste(av, (x, y), mask)
    except Exception:
        pass


def render_arena(
    p1_name: str,
    p1_hp: int,
    p1_secti: bool,
    p2_name: str,
    p2_hp: int,
    p2_secti: bool,
    max_hp: int,
    tur: int,
    maks_tur: int,
    son_log: str = "",
    p1_avatar_bytes: bytes | None = None,
    p2_avatar_bytes: bytes | None = None,
) -> bytes:
    img = Image.new("RGB", (W, H), _BG)
    d   = ImageDraw.Draw(img)

    f_title = _font(20, bold=True)
    f_name  = _font(16, bold=True)
    f_body  = _font(14)
    f_small = _font(13)
    f_tiny  = _font(12)

    AV   = 64          # avatar size
    AV_Y = 52          # avatar top-y
    BAR_W = 340
    BAR_H = 26
    BAR_R = 6
    BAR_Y = AV_Y + AV + 16
    LOG_Y = BAR_Y + BAR_H + 42

    # ── Header ────────────────────────────────────────────────────────────────
    d.text((W // 2, 22), "A R E N A   D Ö V Ü Ş Ü", font=f_title, fill=_WHITE, anchor="mm")
    d.text((W - 20, 22), f"Tur {tur} / {maks_tur}", font=f_tiny, fill=_GRAY, anchor="rm")
    d.line([(20, 40), (W - 20, 40)], fill=_ACCENT, width=2)

    # ── VS etiketi ────────────────────────────────────────────────────────────
    d.text((W // 2, AV_Y + AV // 2), "VS", font=f_name, fill=_ACCENT, anchor="mm")

    # ── Oyuncu sütunları ─────────────────────────────────────────────────────
    for i, (name, hp, secti, av_bytes) in enumerate([
        (p1_name, p1_hp, p1_secti, p1_avatar_bytes),
        (p2_name, p2_hp, p2_secti, p2_avatar_bytes),
    ]):
        # P1 sol kenarda, P2 sağ kenarda ama bar genişlikleri eşit
        bx = 20 if i == 0 else W - 20 - BAR_W

        # Avatar
        if av_bytes:
            _paste_avatar(img, av_bytes, bx, AV_Y, AV)
        tx = bx + (AV + 10 if av_bytes else 0)

        # İsim
        short = (name[:17] + "…") if len(name) > 17 else name
        d.text((tx, AV_Y + 4), short, font=f_name, fill=_WHITE)

        # Durum
        if secti:
            d.text((tx, AV_Y + 26), "Secimini yapti  v", font=f_small, fill=_GREEN)
        else:
            d.text((tx, AV_Y + 26), "Bekleniyor...", font=f_small, fill=_GRAY)

        # HP bar arkaplanı
        d.rounded_rectangle([bx, BAR_Y, bx + BAR_W, BAR_Y + BAR_H], radius=BAR_R, fill=_BAR_BG)

        # HP bar dolgu (renk: yeşil → sarı → kırmızı)
        pct = max(0.0, hp / max_hp)
        fw  = max(BAR_R * 2, int(BAR_W * pct))
        clr = _GREEN if pct > 0.6 else (_YELLOW if pct > 0.3 else _RED)
        d.rounded_rectangle([bx, BAR_Y, bx + fw, BAR_Y + BAR_H], radius=BAR_R, fill=clr)

        # HP yüzde metni (bar üzerinde, sağa yaslanmış)
        pct_txt = f"{round(pct * 100)}%"
        d.text((bx + BAR_W - 6, BAR_Y + BAR_H // 2), pct_txt, font=f_small, fill=_WHITE, anchor="rm")

        # HP sayısal değer
        d.text((bx, BAR_Y + BAR_H + 8), f"{hp} / {max_hp} HP", font=f_tiny, fill=_GRAY)

    # ── Son Eylem ─────────────────────────────────────────────────────────────
    if son_log:
        d.line([(20, LOG_Y - 10), (W - 20, LOG_Y - 10)], fill=_CARD, width=1)
        d.text((20, LOG_Y), "Son Eylem", font=f_tiny, fill=_GRAY)
        clean = son_log.replace("**", "").replace("*", "")
        for j, line in enumerate(clean.split("\n")[:3]):
            d.text((20, LOG_Y + 18 + j * 20), line, font=f_body, fill=_WHITE)

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
