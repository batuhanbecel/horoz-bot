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


def hierarchy_ok(interaction: discord.Interaction, target: discord.Member) -> str | None:
    """Hiyerarşi/yetki kontrolü. Hata mesajı döner (None = OK)."""
    if not interaction.guild:
        return "Bu komut sadece sunucuda çalışır."

    bot_member = interaction.guild.me
    if bot_member is None:
        return "Bot bilgisi alınamadı."

    if target.id == interaction.user.id:
        return "Kendinize bu işlemi yapamazsınız."
    if target.id == bot_member.id:
        return "Bana bu işlemi yapamazsınız. 🐓"
    if target.id == interaction.guild.owner_id:
        return "Sunucu sahibine bu işlem yapılamaz."

    # Kullanıcı sunucu sahibiyse hiyerarşi kontrolü atlanabilir
    if interaction.user.id != interaction.guild.owner_id:
        # interaction.user Member tipinde olmalı (slash komutu sunucuda)
        if isinstance(interaction.user, discord.Member):
            if target.top_role >= interaction.user.top_role:
                return "Bu üyenin rolü sizin rolünüzden yüksek veya eşit."

    if target.top_role >= bot_member.top_role:
        return "Bu üyenin rolü botun rolünden yüksek veya eşit."

    return None
