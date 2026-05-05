import discord
import aiohttp
import os
import random
from datetime import datetime, timezone

_GIPHY_KEY = os.getenv("GIPHY_API_KEY", "")


async def giphy(tag: str) -> str | None:
    """Giphy search API'den rastgele bir GIF URL'si döndürür. Hata olursa None."""
    if not _GIPHY_KEY:
        return None
    url = (
        "https://api.giphy.com/v1/gifs/search"
        f"?api_key={_GIPHY_KEY}&q={tag}&limit=25&rating=pg-13"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status != 200:
                    return None
                payload = await r.json()
                results = payload.get("data", [])
                if not results:
                    return None
                return random.choice(results)["images"]["original"]["url"]
    except Exception:
        return None

SEKIZ_TOP_YANIT = [
    "Kesinlikle evet.", "Evet, şüphesiz.", "Bence evet.",
    "Muhtemelen evet.", "Olumlu görünüyor.", "Evet.",
    "İşaretler evet diyor.", "En iyi ihtimalle evet.",
    "Şu an cevap veremiyorum, tekrar sor.", "Daha sonra tekrar sor.",
    "Daha iyi söylemesem olur.", "Şu an tahmin edemiyorum.",
    "Bunun üzerine durmana gerek yok.", "Cevap bulanık.",
    "Hayır.", "Görünüşe göre hayır.", "Hayırla dön.",
    "Çok şüpheli.", "Pek sanmıyorum.", "Kesinlikle hayır.",
]

TÜRKÇE_AYLAR = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}


def fun_embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.timestamp = discord.utils.utcnow()
    return e


def normalize_saat(saat: str) -> str:
    """'20.00' → '20:00', '2000' → '20:00', '20:00' → '20:00'"""
    saat = saat.strip()
    if "." in saat and ":" not in saat:
        return saat.replace(".", ":")
    if saat.isdigit() and len(saat) == 4:
        return f"{saat[:2]}:{saat[2:]}"
    return saat


def parse_datetime(tarih: str, saat: str) -> datetime | None:
    """'25 Mayıs 2026' veya '25.05.2026' + '20:00' → UTC datetime"""
    tarih = tarih.strip()
    saat = normalize_saat(saat.strip())

    for fmt in ("%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(f"{tarih} {saat}", fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    parts = tarih.split()
    if len(parts) == 3:
        gun, ay_str, yil = parts
        ay = TÜRKÇE_AYLAR.get(ay_str.lower())
        if ay:
            try:
                h, m = (int(x) for x in (saat.split(":") + ["0"])[:2])
                return datetime(int(yil), ay, int(gun), h, m, tzinfo=timezone.utc)
            except (ValueError, IndexError):
                pass

    return None
