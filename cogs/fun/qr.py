"""
cogs/fun/qr.py — QR kod oluşturucu
"""
from __future__ import annotations

import logging
import urllib.parse

import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import c_container, c_media, c_section, c_separator, c_text, c_thumbnail, respond

log = logging.getLogger("horoz_bot.qr")


class QR(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="qr", description="Metin veya link için QR kod oluştur")
    @app_commands.describe(metin="QR kodda kodlanacak metin veya URL")
    async def qr(self, interaction: discord.Interaction, metin: str):
        encoded = urllib.parse.quote(metin, safe="")
        url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={encoded}"
        truncated = metin[:100] + ("..." if len(metin) > 100 else "")
        await respond(interaction, c_container(
            c_section(
                c_text(f"## 📱 QR Kod\n\n`{truncated}`"),
                accessory=c_thumbnail(url),
            ),
            c_separator(),
            c_media(url),
        ))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("qr hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(QR(bot))
