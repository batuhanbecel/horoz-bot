import discord
import re
from datetime import timedelta


def parse_duration(text: str) -> timedelta | None:
    match = re.fullmatch(r"(\d+)([smhd])", text.strip().lower())
    if not match:
        return None
    v, u = int(match.group(1)), match.group(2)
    return {"s": timedelta(seconds=v), "m": timedelta(minutes=v),
            "h": timedelta(hours=v),   "d": timedelta(days=v)}[u]


def _emb(title: str, desc: str = "", color: discord.Color = discord.Color.red()) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text="Horoz Bot • Moderasyon")
    e.timestamp = discord.utils.utcnow()
    return e


def hierarchy_ok(interaction: discord.Interaction, target: discord.Member) -> str | None:
    if target == interaction.user:
        return "Kendinize bu işlemi yapamazsınız."
    if target.top_role >= interaction.user.top_role:
        return "Bu üyenin rolü sizin rolünüzden yüksek veya eşit."
    if target.top_role >= interaction.guild.me.top_role:
        return "Bu üyenin rolü botun rolünden yüksek veya eşit."
    return None
