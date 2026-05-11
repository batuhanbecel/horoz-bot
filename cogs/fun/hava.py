"""
cogs/fun/hava.py — Hava durumu (wttr.in)
"""
from __future__ import annotations

import logging
import urllib.parse

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import c_container, c_error, c_separator, c_text, respond

log = logging.getLogger("horoz_bot.hava")


class Hava(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hava", description="Hava durumu")
    @app_commands.describe(sehir="Şehir adı (örn: Istanbul, Ankara, Izmir)")
    async def hava(self, interaction: discord.Interaction, sehir: str):
        city = urllib.parse.quote(sehir)
        url = f"https://wttr.in/{city}?format=3"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return await respond(interaction, c_error("Hava durumu alınamadı."), ephemeral=True)
                text = await r.text()
        body = f"`{text.strip()}`"
        await respond(interaction, c_container(
            c_text(f"## 🌤️ Hava Durumu — {sehir.title()}\n\n{body}"),
            c_separator(),
            c_text("-# Kaynak: wttr.in")
        ))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("hava hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Hava(bot))
