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

from .._v2 import c_container, c_separator, c_text, respond

log = logging.getLogger("horoz_bot.sifre")


class ShowPasswordButton(discord.ui.Button):
    def __init__(self, password: str):
        super().__init__(label="🔓 Şifreyi Göster", style=discord.ButtonStyle.primary)
        self.password = password

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        self.label = "👀 Gösterildi"
        self.style = discord.ButtonStyle.secondary
        # Re-send with revealed password
        container = c_container(
            c_text(f"## 🔐 Şifre\n\n`{self.password}`"),
            c_separator(),
            c_text("-# Bu şifreyi kopyalayıp güvenli bir yerde saklayın."),
        )
        await interaction.response.edit_message(components=[container.to_component_dict()], view=self.view)


class Sifre(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sifre", description="Güçlü rastgele şifre üret")
    @app_commands.describe(uzunluk="Şifre uzunluğu (varsayılan: 16, max: 64)")
    async def sifre(self, interaction: discord.Interaction, uzunluk: int = 16):
        length = max(4, min(64, uzunluk))
        chars = string.ascii_letters + string.digits + "!@#$%^&*-_+=?"
        password = "".join(random.SystemRandom().choice(chars) for _ in range(length))
        view = discord.ui.View(timeout=60)
        view.add_item(ShowPasswordButton(password))
        container = c_container(
            c_text(f"## 🔐 Şifre\n\n||`{password}`||"),
            c_separator(),
            c_text("-# Şifreyi görmek için butona basın"),
        )
        msg = await respond(interaction, container, ephemeral=True, view=view)
        if msg:
            interaction._state.store_view(view, msg.id)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("sifre hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Sifre(bot))
