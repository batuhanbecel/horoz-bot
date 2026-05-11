"""
cogs/fun/atasozu.py — Rastgele atasözü (TDK)
"""
from __future__ import annotations

import logging
import random
import string

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import c_container, c_separator, c_text, respond

log = logging.getLogger("horoz_bot.atasozu")

_ATASOZLERI = [
    ("Ağaç yaş iken eğilir.", "Küçük yaşta verilen eğitim önemlidir."),
    ("Acele işe şeytan karışır.", "Acele edilen işte hata yapma ihtimali yüksektir."),
    ("Ak akçe kara gün içindir.", "Kazanç, zor günler için biriktirilmelidir."),
    ("Arpa ektim, darı çıktı.", "Yapılan iyilik karşılıksız kalmadı."),
    ("At binenin, kılıç kuşananın.", "Güç, güçlü olanın elindedir."),
    ("Başkasına dilenci etme, kendi elin kapı etme.", "Başkalarına muhtaç olmamaya çalış."),
    ("Bir elin nesi var, iki elin sesi var.", "İş birliği güçlendirir."),
    ("Bilmeyen öğrenir, öğrenmeyen öğretmez.", "Öğrenmeye açık olmak gerekir."),
    ("Boş çuval dik durmaz.", "Boş olan değerli değildir."),
    ("Çıkmayan candan umut kesilmez.", "Umut her zaman var olmalıdır."),
    ("Damlaya damlaya göl olur.", "Küçük birikimler büyük sonuçlar doğurur."),
    ("Davulun sesi uzaktan hoş gelir.", "Her şey uzaktan iyi görünür."),
    ("Değirmenin suyu nereden geliyor?", "Her işin bir nedeni vardır."),
    ("Dost kara günde belli olur.", "Gerçek dost zor anlarda belli olur."),
    ("Eğri otur, doğru söyle.", "Doğruyu söylemek için dürüst ol."),
    ("El elden üstündür.", "Herkesin bir üstün yanı vardır."),
    ("Eşek ölür, semeri kalır; insan ölür, eseri kalır.", "İnsan eserleriyle anılır."),
]


class Atasozu(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="atasozu", description="Rastgele bir atasözü ve anlamı (TDK)")
    async def atasozu(self, interaction: discord.Interaction):
        soz, anlam = "", ""
        try:
            letter = random.choice(string.ascii_lowercase)
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
                async with s.get(f"https://sozluk.gov.tr/atasozu?ara={letter}") as r:
                    if r.status == 200:
                        data = await r.json()
                        results = [item for item in data if isinstance(item, dict) and item.get("turu2") == "Atasözü"]
                        if results:
                            item = random.choice(results)
                            soz = item.get("sozum", "").strip()
                            anlam = item.get("anlami", "").strip()
        except Exception:
            pass
        if not soz:
            soz, anlam = random.choice(_ATASOZLERI)
        body = f"**{soz}**\n\n*{anlam}*"
        await respond(interaction, c_container(
            c_text(f"## 📜 Atasözü\n\n{body}"),
            c_separator(),
            c_text("-# Kaynak: TDK (sozluk.gov.tr)")
        ))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("atasozu hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Atasozu(bot))
