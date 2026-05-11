"""
cogs/fun/babasakasi.py — Klasik baba şakası
"""
from __future__ import annotations

import logging
import random

import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import c_container, c_text, respond

log = logging.getLogger("horoz_bot.babasakasi")

_BABASAKALARI = [
    ("Çocuk: Baba, neden elektrik süpürgesi ses çıkarır?", "Baba: Çünkü içinde kedi varmış da çıkamamış!"),
    ("Çocuk: Baba, neden gökyüzü mavidir?", "Baba: Çünkü yukarıda birileri maviyi seviyor!"),
    ("Çocuk: Baba, su neden ıslak?", "Baba: Islak değil, sadece sen öyle hissediyorsun!"),
    ("Çocuk: Baba, neden ayak parmaklarım beş tane?", "Baba: Altıncıyı bulamadığın için!"),
    ("Çocuk: Baba, neden tavuklar uçamaz?", "Baba: Çünkü uçak bileti pahalı!"),
    ("Çocuk: Baba, neden uyuyoruz?", "Baba: Çünkü uyanıkken de uyuyor gibiyiz!"),
    ("Çocuk: Baba, neden çikolata tatlıdır?", "Baba: Çünkü acı olsa yemezsin!"),
    ("Çocuk: Baba, neden saçlarım beyazlanıyor?", "Baba: Çünkü akıllı oluyorsun!"),
    ("Çocuk: Baba, neden televizyon konuşmuyor?", "Baba: Seninle konuşmaktan utanıyor!"),
    ("Çocuk: Baba, neden buz gibi?", "Baba: Çünkü buz onun soyadı!"),
    ("Çocuk: Baba, neden arılar bal yapar?", "Baba: Para kazanmak için!"),
    ("Çocuk: Baba, neden gözlük takıyorsun?", "Baba: Seni daha net görmek için!"),
]


class Babasakasi(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="babasakasi", description="Klasik bir baba şakası")
    async def babasakasi(self, interaction: discord.Interaction):
        child, father = random.choice(_BABASAKALARI)
        text = f"{child}\n\n**{father}**"
        await respond(interaction, c_container(c_text(f"## 🧔 Baba Şakası\n\n{text}")))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("babasakasi hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Babasakasi(bot))
