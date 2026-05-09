"""
cogs/utility/snipe.py — /snipe: Silinen son mesajı gösterir.
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from .._v2 import c_text, c_section, c_thumbnail, c_separator, c_container, respond

_snipe_cache: dict[int, dict] = {}


class Snipe(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        _snipe_cache[message.channel.id] = {
            "author_name":   message.author.display_name,
            "author_avatar": str(message.author.display_avatar.url),
            "content":       message.content or "",
            "attachments":   [(a.filename, a.proxy_url) for a in message.attachments],
            "deleted_at":    discord.utils.utcnow(),
        }

    @app_commands.command(name="snipe", description="Bu kanalda silinen son mesajı gösterir.")
    @app_commands.guild_only()
    async def snipe(self, interaction: discord.Interaction):
        data = _snipe_cache.get(interaction.channel_id)  # type: ignore[arg-type]
        if not data:
            await respond(
                interaction,
                c_container(
                    c_text("## 👻 Snipe"),
                    c_separator(),
                    c_text("Bu kanalda yakın zamanda silinen mesaj bulunamadı."),
                ),
                ephemeral=True,
            )
            return

        ts      = int(data["deleted_at"].timestamp())
        content = data["content"]
        attaches: list[tuple[str, str]] = data["attachments"]

        body = content if content else "_[içerik yok]_"
        if attaches:
            links = "  ".join(f"[`{fn}`]({url})" for fn, url in attaches[:5])
            body += f"\n-# 📎 {links}"

        await respond(
            interaction,
            c_container(
                c_section(
                    c_text(f"## 👻 Snipe\n-# <t:{ts}:R> silindi"),
                    accessory=c_thumbnail(data["author_avatar"]),
                ),
                c_separator(),
                c_text(f"**{data['author_name']}** yazdı:\n{body}"),
            ),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Snipe(bot))
