"""Şarkı sözü çekme — lyrics.ovh ücretsiz API'si.

API key gerekmez. Track title'ından artist + song parse edilir,
ardından lyrics.ovh sorgulanır.
"""
from __future__ import annotations

import re
import aiohttp
from urllib.parse import quote


# Title temizleme: parantez/köşeli parantez içleri ve common keywordler
_PAREN_RE   = re.compile(r"\([^)]*\)")
_BRACKET_RE = re.compile(r"\[[^\]]*\]")
_DROP_WORDS = [
    "official video", "official audio", "official music video", "official",
    "music video", "lyric video", "lyric", "lyrics", "audio", "video",
    "hd", "hq", "4k", "8k", "live", "remastered", "remaster",
    "explicit", "clean", "extended", "edit", "radio edit",
    "feat", "ft", "ft.", "feat.",
]


def _clean_title(raw: str) -> str:
    """YouTube title gürültüsünü temizle."""
    s = _PAREN_RE.sub(" ", raw)
    s = _BRACKET_RE.sub(" ", s)
    for word in _DROP_WORDS:
        s = re.sub(rf"\b{re.escape(word)}\b\.?", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip(" -—_.|")
    return s


def parse_artist_title(track_title: str) -> tuple[str, str]:
    """Track title'ından (artist, song) çıkarır. Mevcut separator'lara göre böler."""
    cleaned = _clean_title(track_title)
    for sep in (" - ", " — ", " – ", " | ", ": "):
        if sep in cleaned:
            artist, _, song = cleaned.partition(sep)
            return (artist.strip(), song.strip())
    # Fallback: tüm title'ı şarkı adı say
    return ("", cleaned)


async def fetch_lyrics(artist: str, title: str) -> str | None:
    """lyrics.ovh API'sinden şarkı sözünü çeker. Bulunamazsa None."""
    if not title:
        return None
    artist_q = quote(artist.strip()) if artist.strip() else "unknown"
    title_q  = quote(title.strip())
    url = f"https://api.lyrics.ovh/v1/{artist_q}/{title_q}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return None
                data = await r.json(content_type=None)
                lyrics = (data.get("lyrics") or "").strip()
                # API bazen başlık satırı bırakıyor — ilk boş satıra kadar bunu siliyoruz
                lyrics = re.sub(r"^Paroles de la chanson[^\n]*\n+", "", lyrics)
                return lyrics or None
    except (aiohttp.ClientError, TimeoutError):
        return None
    except Exception as e:
        print(f"[lyrics] fetch hatası: {e}")
        return None


async def fetch_for_track(track_title: str) -> tuple[str, str, str | None]:
    """Track title'ından artist+song parse + lyrics fetch. (artist, title, lyrics)."""
    artist, title = parse_artist_title(track_title)
    lyrics = await fetch_lyrics(artist, title)
    # Artist boşsa veya bulunamadıysa, tüm title ile bir kez daha dene
    if not lyrics and artist:
        lyrics = await fetch_lyrics("", f"{artist} {title}")
    return (artist, title, lyrics)


# ── Extension entry-point (required by discord.py) ────────────────────────────

async def setup(bot: commands.Bot):
    """Helper module — no cog to load, but required for extension discovery."""
    pass
