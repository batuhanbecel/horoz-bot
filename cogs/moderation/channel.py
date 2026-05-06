import discord
from discord import app_commands
from discord.ext import commands
from .._v2 import (
    COLORS, c_card, c_action_card, respond, followup as v2_followup, error_response,
)


class ChannelMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    kanal = app_commands.Group(
        name="kanal",
        description="Kanal yönetim komutları",
    )

    # /kanal temizle
    @kanal.command(name="temizle", description="Belirtilen sayıda mesajı siler.")
    @app_commands.describe(miktar="Silinecek mesaj sayısı (1-100)")
    async def temizle(self, interaction: discord.Interaction, miktar: app_commands.Range[int, 1, 100]):
        thumb = str(interaction.client.user.display_avatar.url)
        if not interaction.user.guild_permissions.manage_messages:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Mesajları Yönet** yetkisi gereklidir.", thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=miktar)
        await v2_followup(interaction, c_action_card(
            "🧹 Kanal Temizlendi",
            target_avatar=thumb,
            fields=[
                ("📌 Kanal", interaction.channel.mention),
                ("🗑️ Silinen Mesaj", f"`{len(deleted)}`"),
                ("👮 Moderatör", interaction.user.mention),
            ],
            color=COLORS.SUCCESS,
        ), ephemeral=True)

    # /kanal yavaşmod
    @kanal.command(name="yavaşmod", description="Kanal yavaş modunu ayarlar (0 = kapalı).")
    @app_commands.describe(saniye="Bekleme süresi saniye (0-21600)", kanal="Kanal (boş = mevcut)")
    async def yavaşmod(
        self,
        interaction: discord.Interaction,
        saniye: app_commands.Range[int, 0, 21600],  # type: ignore[type-arg]
        kanal: discord.TextChannel = None,
    ):
        thumb = str(interaction.client.user.display_avatar.url)
        if not interaction.user.guild_permissions.manage_channels:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Kanalları Yönet** yetkisi gereklidir.", thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
            )
        target = kanal or interaction.channel
        await target.edit(slowmode_delay=saniye)
        if saniye == 0:
            await respond(interaction, c_action_card(
                "🐢 Yavaş Mod Kapatıldı",
                target_avatar=thumb,
                fields=[
                    ("📌 Kanal", target.mention),
                    ("👮 Moderatör", interaction.user.mention),
                ],
                color=COLORS.SUCCESS,
            ), ephemeral=True)
        else:
            await respond(interaction, c_action_card(
                "🐢 Yavaş Mod Açıldı",
                target_avatar=thumb,
                fields=[
                    ("📌 Kanal", target.mention),
                    ("⏱️ Süre", f"`{saniye}` saniye"),
                    ("👮 Moderatör", interaction.user.mention),
                ],
                color=COLORS.WARNING,
            ), ephemeral=True)

    # /kanal kilitle
    @kanal.command(name="kilitle", description="Kanalı kilitler, üyeler mesaj gönderemez.")
    @app_commands.describe(kanal="Kilitlenecek kanal (boş = mevcut)", sebep="Kilitleme sebebi")
    async def kilitle(self, interaction: discord.Interaction, kanal: discord.TextChannel = None, sebep: str = "Belirtilmedi"):
        thumb = str(interaction.client.user.display_avatar.url)
        if not interaction.user.guild_permissions.manage_channels:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Kanalları Yönet** yetkisi gereklidir.", thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
            )
        target = kanal or interaction.channel
        ow = target.overwrites_for(interaction.guild.default_role)
        ow.send_messages = False
        await target.set_permissions(interaction.guild.default_role, overwrite=ow, reason=f"{interaction.user}: {sebep}")

        await respond(interaction, c_action_card(
            "🔒 Kanal Kilitlendi",
            target_avatar=thumb,
            fields=[
                ("📌 Kanal", target.mention),
                ("👮 Moderatör", interaction.user.mention),
                ("📝 Sebep", sebep),
            ],
            footer=f"Sunucu: {interaction.guild.name}",
            color=COLORS.DANGER,
        ))

    # /kanal kilit-aç
    @kanal.command(name="kilit-aç", description="Kilitli kanalın kilidini açar.")
    @app_commands.describe(kanal="Kilidi açılacak kanal (boş = mevcut)")
    async def kilit_ac(self, interaction: discord.Interaction, kanal: discord.TextChannel = None):
        thumb = str(interaction.client.user.display_avatar.url)
        if not interaction.user.guild_permissions.manage_channels:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Kanalları Yönet** yetkisi gereklidir.", thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
            )
        target = kanal or interaction.channel
        ow = target.overwrites_for(interaction.guild.default_role)
        ow.send_messages = None
        await target.set_permissions(interaction.guild.default_role, overwrite=ow)

        await respond(interaction, c_action_card(
            "🔓 Kanal Kilidi Açıldı",
            target_avatar=thumb,
            fields=[
                ("📌 Kanal", target.mention),
                ("👮 Moderatör", interaction.user.mention),
            ],
            color=COLORS.SUCCESS,
        ))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Botun bu işlem için yeterli yetkisi yok." \
            if isinstance(error, app_commands.BotMissingPermissions) else str(error)
        await error_response(interaction, msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelMod(bot))
