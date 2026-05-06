import discord
from discord.ext import commands
import os
from .._v2 import channel_send

LOG_CHANNEL_ID     = int(os.getenv("LOG_CHANNEL_ID",     "1326534476213256192"))
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))
LEAVE_EMOJI_ID     = int(os.getenv("LEAVE_EMOJI_ID",     "0"))


async def get_audit(guild: discord.Guild, action: discord.AuditLogAction, target_id: int = None, limit: int = 1):
    try:
        async for entry in guild.audit_logs(action=action, limit=limit):
            if target_id is None or entry.target.id == target_id:
                return entry
    except (discord.Forbidden, discord.HTTPException):
        pass
    return None


class LogBase(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def log(self, guild: discord.Guild, *components: dict) -> None:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(LOG_CHANNEL_ID)
            except Exception:
                return
        try:
            await channel_send(ch, *components)
        except (discord.Forbidden, discord.HTTPException):
            pass
