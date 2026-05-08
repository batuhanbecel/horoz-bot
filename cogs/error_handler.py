import discord
from discord import app_commands
from discord.ext import commands
import logging

from .._v2 import COLORS, c_card, respond, error_response

log = logging.getLogger("horoz_bot")


class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Global app command error handler — modern V2 cards."""
        if isinstance(error, app_commands.MissingPermissions):
            msg = "Bu komutu kullanmak için gereken yetkilere sahip değilsiniz."
        elif isinstance(error, app_commands.BotMissingPermissions):
            msg = f"Botun gereken yetkileri eksik: {', '.join(error.missing_permissions)}"
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏰ Komut beklemede. `{error.retry_after:.1f}` saniye sonra tekrar deneyin."
        elif isinstance(error, app_commands.NoPrivateMessage):
            msg = "Bu komut sadece sunucularda çalışır."
        elif isinstance(error, app_commands.CheckFailure):
            msg = "Bu komutu kullanma yetkiniz yok."
        elif isinstance(error, app_commands.CommandInvokeError):
            original = error.original
            log.error(f"CommandInvokeError in {interaction.command.name}: {original}", exc_info=original)
            msg = f"Komut çalıştırılırken bir hata oluştu.\n```\n{original}\n```"
        else:
            log.error(f"Unhandled app command error: {error}", exc_info=error)
            msg = f"Beklenmeyen bir hata oluştu.\n```\n{error}\n```"

        if interaction.response.is_done():
            await error_response(interaction, msg)
        else:
            await respond(interaction, c_card("## ❌ Hata", body=msg, color=COLORS.DANGER), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorHandler(bot))
