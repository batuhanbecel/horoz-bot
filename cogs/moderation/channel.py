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
        guild_only=True,
    )

    # /kanal temizle
    @kanal.command(name="temizle", description="Belirtilen sayıda mesajı siler.")
    @app_commands.describe(miktar="Silinecek mesaj sayısı (1-100)")
    async def temizle(self, interaction: discord.Interaction, miktar: app_commands.Range[int, 1, 100]):
        if not interaction.user.guild_permissions.manage_messages:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Mesajları Yönet** yetkisi gereklidir.", color=COLORS.DANGER),
                ephemeral=True,
            )

        # Kanal referansı: interaction.channel partial olabilir, fresh olarak al
        channel = interaction.guild.get_channel(interaction.channel_id) if interaction.guild else interaction.channel
        if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
            return await respond(interaction,
                c_card("## ❌ Geçersiz Kanal", body="Bu komut sadece metin kanallarında çalışır.", color=COLORS.DANGER),
                ephemeral=True,
            )

        # Botun bu kanalda yetkisi var mı?
        me = interaction.guild.me
        perms = channel.permissions_for(me)
        if not (perms.manage_messages and perms.read_message_history):
            return await respond(interaction,
                c_card(
                    "## ❌ Botun Yetkisi Yok",
                    body=f"Botun {channel.mention} kanalında **Mesajları Yönet** + **Mesaj Geçmişini Oku** yetkisi gerekiyor.",
                    color=COLORS.DANGER,
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await channel.purge(
                limit=miktar,
                bulk=True,
                reason=f"{interaction.user}: /kanal temizle ({miktar})",
            )
        except discord.Forbidden:
            return await v2_followup(interaction,
                c_card("## ❌ Erişim Reddedildi", body="Mesajları silme izni reddedildi.", color=COLORS.DANGER),
                ephemeral=True,
            )
        except discord.HTTPException as e:
            return await v2_followup(interaction,
                c_card("## ❌ Silme Hatası", body=f"```{e}```", color=COLORS.DANGER),
                ephemeral=True,
            )

        if not deleted:
            return await v2_followup(interaction,
                c_card(
                    "## ⚠️ Mesaj Silinmedi",
                    body=(
                        f"`0` mesaj silindi. Olası sebepler:\n"
                        f"• Kanal zaten boş\n"
                        f"• Tüm mesajlar **14 günden eski** (toplu silme limiti)\n"
                        f"• Ek izin sorunu"
                    ),
                    color=COLORS.WARNING,
                ),
                ephemeral=True,
            )

        await v2_followup(interaction, c_action_card(
            "🧹 Kanal Temizlendi",
            fields=[
                ("📌 Kanal", channel.mention),
                ("🗑️ Silinen", f"`{len(deleted)}` / `{miktar}` mesaj"),
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
        if not interaction.user.guild_permissions.manage_channels:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Kanalları Yönet** yetkisi gereklidir.", color=COLORS.DANGER),
                ephemeral=True,
            )
        target = kanal or interaction.channel
        try:
            await target.edit(slowmode_delay=saniye)
        except discord.Forbidden:
            return await respond(interaction,
                c_card("## ❌ Botun Yetkisi Yok", body=f"Botun {target.mention} kanalını düzenleme yetkisi yok.", color=COLORS.DANGER),
                ephemeral=True,
            )

        if saniye == 0:
            await respond(interaction, c_action_card(
                "🐢 Yavaş Mod Kapatıldı",
                fields=[
                    ("📌 Kanal", target.mention),
                    ("👮 Moderatör", interaction.user.mention),
                ],
                color=COLORS.SUCCESS,
            ), ephemeral=True)
        else:
            await respond(interaction, c_action_card(
                "🐢 Yavaş Mod Açıldı",
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
        if not interaction.user.guild_permissions.manage_channels:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Kanalları Yönet** yetkisi gereklidir.", color=COLORS.DANGER),
                ephemeral=True,
            )
        target = kanal or interaction.channel
        ow = target.overwrites_for(interaction.guild.default_role)
        ow.send_messages = False
        try:
            await target.set_permissions(interaction.guild.default_role, overwrite=ow, reason=f"{interaction.user}: {sebep}")
        except discord.Forbidden:
            return await respond(interaction,
                c_card("## ❌ Botun Yetkisi Yok", body=f"Botun {target.mention} kanalında izin düzenleme yetkisi yok.", color=COLORS.DANGER),
                ephemeral=True,
            )

        await respond(interaction, c_action_card(
            "🔒 Kanal Kilitlendi",
            fields=[
                ("📌 Kanal", target.mention),
                ("👮 Moderatör", interaction.user.mention),
                ("📝 Sebep", sebep),
            ],
            color=COLORS.DANGER,
        ))

    # /kanal kilit-aç
    @kanal.command(name="kilit-aç", description="Kilitli kanalın kilidini açar.")
    @app_commands.describe(kanal="Kilidi açılacak kanal (boş = mevcut)")
    async def kilit_ac(self, interaction: discord.Interaction, kanal: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_channels:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Kanalları Yönet** yetkisi gereklidir.", color=COLORS.DANGER),
                ephemeral=True,
            )
        target = kanal or interaction.channel
        ow = target.overwrites_for(interaction.guild.default_role)
        ow.send_messages = None
        try:
            await target.set_permissions(interaction.guild.default_role, overwrite=ow)
        except discord.Forbidden:
            return await respond(interaction,
                c_card("## ❌ Botun Yetkisi Yok", body=f"Botun {target.mention} kanalında izin düzenleme yetkisi yok.", color=COLORS.DANGER),
                ephemeral=True,
            )

        await respond(interaction, c_action_card(
            "🔓 Kanal Kilidi Açıldı",
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
