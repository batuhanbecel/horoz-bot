"""
cogs/fun/altin.py — Güncel altın fiyatları (Truncgil)
"""
from __future__ import annotations

import logging

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import c_container, c_error, c_text, respond

log = logging.getLogger("horoz_bot.altin")


class Altin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="altin", description="Güncel altın fiyatları")
    async def altin(self, interaction: discord.Interaction):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get("https://finans.truncgil.com/v3/today.json") as r:
                if r.status != 200:
                    return await respond(interaction, c_error("Altın verisi alınamadı."), ephemeral=True)
                data = await r.json()
        lines: list[str] = []
        keys = ["Gram_Altin", "Ceyrek_Altin", "Yarim_Altin", "Tam_Altin", "Ons_Altin", "USD", "EUR"]
        for key in keys:
            if key not in data or not isinstance(data[key], dict):
                continue
            satis = data[key].get("satis", data[key].get("Selling", "?"))
            alis = data[key].get("alis", data[key].get("Buying", "?"))
            name = key.replace("_", " ")
            lines.append(f"**{name}:** Alış {alis} / Satış {satis}")
        if not lines:
            return await respond(interaction, c_error("Veri formatı bozuk."), ephemeral=True)
        body = "\n".join(lines) + "\n\n-# Kaynak: finans.truncgil.com"
        await respond(interaction, c_container(c_text(f"## 🏅 Altın & Döviz\n\n{body}")))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("altin hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Altin(bot))
