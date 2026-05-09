"""
cogs/server/sayac.py — /sayaç: Sunucu istatistik kanalları.
Her 10 dakikada bir ses kanalı isimlerini günceller.
"""
from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
from database import db as database
from .._v2 import (
    c_text, c_separator, c_container, c_action_card,
    edit_original, error_response,
)

_KEYS = ("sayac_member_ch", "sayac_bot_ch", "sayac_online_ch")

_LABELS = {
    "sayac_member_ch": lambda t, _b, _o: f"👥 Toplam Üye: {t}",
    "sayac_bot_ch":    lambda _t, b, _o: f"🤖 Bot: {b}",
    "sayac_online_ch": lambda _t, _b, o: f"🟢 Online: {o}",
}


async def _load_channel_ids(guild_id: int) -> dict[str, int | None]:
    result: dict[str, int | None] = {}
    for key in _KEYS:
        val = await database.get_setting(guild_id, key)
        result[key] = int(val) if val else None
    return result


async def _update_guild(guild: discord.Guild) -> None:
    ids = await _load_channel_ids(guild.id)
    if not any(ids.values()):
        return

    cached = list(guild.members)
    total  = guild.member_count or len(cached)
    bots   = sum(1 for m in cached if m.bot)
    online = sum(1 for m in cached if m.status != discord.Status.offline)

    for key, ch_id in ids.items():
        if not ch_id:
            continue
        ch = guild.get_channel(ch_id)
        if not isinstance(ch, discord.VoiceChannel):
            continue
        new_name = _LABELS[key](total, bots, online)
        if ch.name != new_name:
            try:
                await ch.edit(name=new_name)
            except discord.HTTPException:
                pass


class Sayac(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_loop.start()

    def cog_unload(self) -> None:
        self.update_loop.cancel()

    @tasks.loop(minutes=10)
    async def update_loop(self) -> None:
        for guild in self.bot.guilds:
            try:
                await _update_guild(guild)
            except Exception:
                pass

    @update_loop.before_loop
    async def _before(self) -> None:
        await self.bot.wait_until_ready()

    sayac_group = app_commands.Group(name="sayaç", description="Sunucu istatistik kanalları")

    @sayac_group.command(name="kur", description="İstatistik ses kanalları oluşturur.")
    @app_commands.guild_only()
    async def kur(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.manage_channels:  # type: ignore[union-attr]
            return await error_response(interaction, "**Kanalları Yönet** yetkisi gereklidir.")

        await interaction.response.defer()
        guild = interaction.guild  # type: ignore[assignment]

        try:
            ids = await _load_channel_ids(guild.id)
            if any(ids.values()):
                await edit_original(
                    interaction,
                    c_container(
                        c_text("## ⚠️ Zaten Kurulu"),
                        c_separator(),
                        c_text("Sayaç kanalları zaten var. Önce `/sayaç kaldır` komutunu kullan."),
                    ),
                )
                return

            overwrites = {guild.default_role: discord.PermissionOverwrite(connect=False)}
            category  = await guild.create_category("📊 İstatistikler")
            member_ch = await guild.create_voice_channel("⏳ Yükleniyor...", category=category, overwrites=overwrites)
            bot_ch    = await guild.create_voice_channel("⏳ Yükleniyor...", category=category, overwrites=overwrites)
            online_ch = await guild.create_voice_channel("⏳ Yükleniyor...", category=category, overwrites=overwrites)

            await database.set_setting(guild.id, "sayac_member_ch", str(member_ch.id))
            await database.set_setting(guild.id, "sayac_bot_ch",    str(bot_ch.id))
            await database.set_setting(guild.id, "sayac_online_ch", str(online_ch.id))
            await database.set_setting(guild.id, "sayac_category",  str(category.id))

            await _update_guild(guild)

            await edit_original(
                interaction,
                c_action_card(
                    "✅ Sayaç Kanalları Kuruldu",
                    fields=[
                        ("📊 Kategori",   category.mention),
                        ("🔄 Güncelleme", "Her 10 dakikada bir"),
                    ],
                    footer="Kaldırmak için /sayaç kaldır",
                ),
            )

        except Exception as ex:
            try:
                await edit_original(
                    interaction,
                    c_container(
                        c_text("## ❌ Hata"),
                        c_separator(),
                        c_text(f"```{ex}```"),
                    ),
                )
            except Exception:
                pass

    @sayac_group.command(name="kaldır", description="İstatistik ses kanallarını kaldırır.")
    @app_commands.guild_only()
    async def kaldir(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.manage_channels:  # type: ignore[union-attr]
            return await error_response(interaction, "**Kanalları Yönet** yetkisi gereklidir.")

        await interaction.response.defer()
        guild = interaction.guild  # type: ignore[assignment]

        try:
            ids     = await _load_channel_ids(guild.id)
            cat_val = await database.get_setting(guild.id, "sayac_category")
            deleted = 0

            for key, ch_id in ids.items():
                if ch_id:
                    ch = guild.get_channel(ch_id)
                    if ch:
                        try:
                            await ch.delete()
                            deleted += 1
                        except discord.HTTPException:
                            pass
                await database.set_setting(guild.id, key, "")

            if cat_val:
                cat = guild.get_channel(int(cat_val))
                if cat:
                    try:
                        await cat.delete()
                    except discord.HTTPException:
                        pass
                await database.set_setting(guild.id, "sayac_category", "")

            await edit_original(
                interaction,
                c_action_card(
                    "✅ Sayaç Kanalları Kaldırıldı",
                    fields=[("🗑️ Silinen Kanal", str(deleted))],
                ),
            )

        except Exception as ex:
            try:
                await edit_original(
                    interaction,
                    c_container(
                        c_text("## ❌ Hata"),
                        c_separator(),
                        c_text(f"```{ex}```"),
                    ),
                )
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Sayac(bot))
