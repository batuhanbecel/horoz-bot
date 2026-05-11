"""
cogs/fun/fikra.py — Rastgele Türkçe fıkra
"""
from __future__ import annotations

import logging
import random

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import c_container, c_text, respond

log = logging.getLogger("horoz_bot.fikra")

_FIKRALAR = [
    "Temel Dursun'a demiş ki: 'Senin burnun niye kırmızı?' Dursun: 'Çünkü kırmızı severim.' Temel: 'O zaman niye mor değil?' Dursun: 'Çünkü mor sevmem.'",
    "Temel bir gün hastaneye gitmiş. Doktor: 'Kanser misin?' Temel: 'Hayır, ben Temel\\'im.'",
    "Nasreddin Hoca'ya sormuşlar: 'Hoca, bu tavuğu kaça aldın?' Hoca: 'Beş akçeye.' 'Satarken kaça sattın?' 'Üç akçeye.' 'Niye zarar ettin?' 'Alırken aldım sandım, satarken fark ettim ki tavuk horozmuş.'",
    "Temel'e sormuşlar: 'Dünya kaç günde döner?' Temel: 'Hangi gün dönerse dönsün, ben döner yemem.'",
    "Nasreddin Hoca eve gelmiş, karısı ağlıyor. 'Niye ağlıyorsun?' 'Komşunun tavuğu ölmüş.' 'Peki bizim tavuğumuz ölse ağlar mısın?' 'Ağlarım.' 'Niye?' 'Çünkü bizim komşumuz olur.'",
    "Temel Amerika'ya gitmiş, İngilizce konuşuyor. Adam: 'Where are you from?' Temel: 'From home.'",
    "Bir fakir köye doktor gelmiş, 'Burada veba var mı?' diye sormuş. Köylü: 'Yok, ama zenginlerde var.'",
    "Temel uçakta hostese: 'Bu koltuk niye bu kadar dar?' Hostes: 'Kurtarma yeleği koltuğun altında.' Temel: 'Anladım, o zaman ben kurtulamam.'",
]


class Fikra(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="fikra", description="Rastgele Türkçe fıkra")
    async def fikra(self, interaction: discord.Interaction):
        text = random.choice(_FIKRALAR)
        await respond(interaction, c_container(c_text(f"## 😂 Fıkra\n\n{text}")))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("fikra hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fikra(bot))
