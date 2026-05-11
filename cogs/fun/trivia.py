"""
cogs/fun/trivia.py — Rastgele bilgi yarışması sorusu (OpenTDB)
"""
from __future__ import annotations

import logging
import random
import urllib.parse

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import c_container, c_text, respond

log = logging.getLogger("horoz_bot.trivia")

_TRIVIA = [
    {"soru": "Türkiye'nin en yüksek dağı hangisidir?", "secenekler": ["Ağrı Dağı", "Uludağ", "Erciyes", "Kaçkar Dağı"], "dogru": 0},
    {"soru": "İstanbul'un fethi hangi yılda gerçekleşmiştir?", "secenekler": ["1451", "1453", "1455", "1460"], "dogru": 1},
    {"soru": "Türk bayrağındaki ay ve yıldızın rengi nedir?", "secenekler": ["Sarı", "Beyaz", "Kırmızı", "Siyah"], "dogru": 1},
    {"soru": "Türkiye'nin başkenti hangi şehirdir?", "secenekler": ["İstanbul", "İzmir", "Ankara", "Bursa"], "dogru": 2},
    {"soru": "Nutuk hangi yılda söylenmiştir?", "secenekler": ["1920", "1923", "1927", "1934"], "dogru": 2},
    {"soru": "Dünya'nın en büyük okyanusu hangisidir?", "secenekler": ["Atlantik", "Hint", "Pasifik", "Arktik"], "dogru": 2},
    {"soru": "Python programlama dili hangi yılda yayımlanmıştır?", "secenekler": ["1989", "1991", "1995", "2000"], "dogru": 1},
    {"soru": "Türkiye'nin en uzun nehri hangisidir?", "secenekler": ["Fırat", "Dicle", "Kızılırmak", "Sakarya"], "dogru": 2},
    {"soru": "Işık hızı yaklaşık kaç km/s'dir?", "secenekler": ["150.000", "300.000", "500.000", "1.000.000"], "dogru": 1},
    {"soru": "Dünya'nın uydusu hangisidir?", "secenekler": ["Mars", "Venüs", "Ay", "Jüpiter"], "dogru": 2},
    {"soru": "Bir yılda kaç gün vardır?", "secenekler": ["364", "365", "366", "360"], "dogru": 1},
    {"soru": "İnsan vücudundaki en büyük organ hangisidir?", "secenekler": ["Karaciğer", "Deri", "Akciğer", "Beyin"], "dogru": 1},
    {"soru": "H2O hangi maddenin kimyasal formülüdür?", "secenekler": ["Su", "Tuz", "Kum", "Demir"], "dogru": 0},
    {"soru": "Dünya'nın en yüksek dağı hangisidir?", "secenekler": ["K2", "Everest", "Kilimanjaro", "Mont Blanc"], "dogru": 1},
]


class Trivia(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="trivia", description="Rastgele bir bilgi yarışması sorusu (OpenTDB)")
    async def trivia(self, interaction: discord.Interaction):
        body = ""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
                async with s.get("https://opentdb.com/api.php?amount=1&encode=url3986&type=multiple") as r:
                    if r.status == 200:
                        data = await r.json()
                        results = data.get("results", [])
                        if results:
                            q = results[0]
                            question = urllib.parse.unquote(q.get("question", ""))
                            correct = urllib.parse.unquote(q.get("correct_answer", ""))
                            incorrect = [urllib.parse.unquote(a) for a in q.get("incorrect_answers", [])]
                            all_answers = incorrect + [correct]
                            random.shuffle(all_answers)
                            lines = [f"{i + 1}. {a}" for i, a in enumerate(all_answers)]
                            body = f"**{question}**\n\n" + "\n".join(lines)
                            body += f"\n\n-# Doğru cevap: ||{correct}||\n-# Kategori: {urllib.parse.unquote(q.get('category', '?'))} | Zorluk: {q.get('difficulty', '?')}"
        except Exception:
            pass
        if not body:
            soru = random.choice(_TRIVIA)
            secenekler = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(soru["secenekler"]))
            body = f"{soru['soru']}\n\n{secenekler}\n\n-# Doğru cevap: ||{soru['secenekler'][soru['dogru']]}||"
        await respond(interaction, c_container(c_text(f"## ❓ Trivia\n\n{body}")))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("trivia hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Trivia(bot))
