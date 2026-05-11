"""
cogs/fun/sifre.py — Güçlü rastgele şifre üretici
"""
from __future__ import annotations

import logging
import random
import string

import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import c_container, c_text, respond

log = logging.getLogger("horoz_bot.sifre")


class Sifre(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sifre", description="Güçlü rastgele şifre üret")
    @app_commands.describe(uzunluk="Şifre uzunluğu (varsayılan: 16, max: 64)")
    async def sifre(self, interaction: discord.Interaction, uzunluk: int = 16):
        length = max(4, min(64, uzunluk))
        chars = string.ascii_letters + string.digits + "!@#$%^&*-_+=?"
        password = "".join(random.SystemRandom().choice(chars) for _ in range(length))
        await respond(interaction, c_container(
            c_text(f"## 🔐 Şifre\n\n`{password}`"),
        ), ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("sifre hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Sifre(bot))
