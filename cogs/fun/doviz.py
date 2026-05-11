"""
cogs/fun/doviz.py — Güncel döviz kurları
"""
from __future__ import annotations

import logging

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import c_container, c_error, c_separator, c_text, respond

log = logging.getLogger("horoz_bot.doviz")


class Doviz(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="doviz", description="Güncel döviz kurları (USD, EUR, GBP)")
    async def doviz(self, interaction: discord.Interaction):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get("https://api.exchangerate-api.com/v4/latest/USD") as r:
                if r.status != 200:
                    return await respond(interaction, c_error("Döviz verisi alınamadı."), ephemeral=True)
                data = await r.json()
        try:
            usd_try = float(data["rates"]["TRY"])
            eur_try = usd_try / float(data["rates"]["EUR"])
            gbp_try = usd_try / float(data["rates"]["GBP"])
            body = (
                f"**1 USD** = {usd_try:.3f} ₺\n"
                f"**1 EUR** = {eur_try:.3f} ₺\n"
                f"**1 GBP** = {gbp_try:.3f} ₺"
            )
        except Exception:
            return await respond(interaction, c_error("Veri formatı bozuk."), ephemeral=True)
        await respond(interaction, c_container(
            c_text(f"## 💱 Döviz Kurları\n\n{body}"),
            c_separator(),
            c_text("-# Kaynak: exchangerate-api.com")
        ))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("doviz hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Doviz(bot))
