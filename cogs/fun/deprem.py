"""
cogs/fun/deprem.py — Son Kandilli depremleri
"""
from __future__ import annotations

import logging

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import c_container, c_error, c_text, respond

log = logging.getLogger("horoz_bot.deprem")


class Deprem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="deprem", description="Son Kandilli depremleri")
    @app_commands.describe(limit="Kaç deprem gösterilsin? (1-10, varsayılan: 5)")
    async def deprem(self, interaction: discord.Interaction, limit: int = 5):
        count = max(1, min(10, limit))
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(f"https://api.orhanaydogdu.com.tr/deprem/kandilli/live?limit={count}") as r:
                if r.status != 200:
                    return await respond(interaction, c_error("Deprem verisi alınamadı."), ephemeral=True)
                data = await r.json()
        rows: list[str] = []
        for item in data.get("result", []):
            if not isinstance(item, dict) or not item.get("mag"):
                continue
            loc = item.get("title", "Bilinmiyor")
            mag = item.get("mag", "?")
            depth = item.get("depth", "?")
            date = item.get("date", "?")
            time = item.get("time", "?")
            rows.append(f"**{loc}** — `M{mag}` — Derinlik: {depth}km — {date} {time}")
        body = "\n".join(rows) if rows else "Veri bulunamadı."
        body += "\n\n-# Kaynak: Kandilli Rasathanesi (orhanaydogdu.com.tr)"
        await respond(interaction, c_container(c_text(f"## 🌍 Son Depremler\n\n{body}")))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("deprem hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Deprem(bot))
