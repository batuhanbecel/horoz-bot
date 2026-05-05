import discord
from discord import app_commands
from discord.ext import commands
from ._shared import _emb


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
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Mesajları Yönet** yetkisi gereklidir."), ephemeral=True
            )
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=miktar)
        await interaction.followup.send(
            embed=_emb("🧹 Temizlendi", f"**{len(deleted)}** mesaj silindi.", discord.Color.green()),
            ephemeral=True,
        )

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
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Kanalları Yönet** yetkisi gereklidir."), ephemeral=True
            )
        target = kanal or interaction.channel
        await target.edit(slowmode_delay=saniye)
        if saniye == 0:
            embed = _emb("🕐 Yavaş Mod Kapatıldı", f"{target.mention} kanalında yavaş mod kaldırıldı.", discord.Color.green())
        else:
            embed = _emb("🕐 Yavaş Mod Açıldı", f"{target.mention} kanalında **{saniye} saniye** yavaş mod uygulandı.", discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /kanal kilitle
    @kanal.command(name="kilitle", description="Kanalı kilitler, üyeler mesaj gönderemez.")
    @app_commands.describe(kanal="Kilitlenecek kanal (boş = mevcut)", sebep="Kilitleme sebebi")
    async def kilitle(self, interaction: discord.Interaction, kanal: discord.TextChannel = None, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Kanalları Yönet** yetkisi gereklidir."), ephemeral=True
            )
        target = kanal or interaction.channel
        ow = target.overwrites_for(interaction.guild.default_role)
        ow.send_messages = False
        await target.set_permissions(interaction.guild.default_role, overwrite=ow, reason=f"{interaction.user}: {sebep}")

        embed = _emb("🔒 Kanal Kilitlendi")
        embed.add_field(name="Kanal",     value=target.mention,           inline=True)
        embed.add_field(name="Moderatör", value=interaction.user.mention, inline=True)
        embed.add_field(name="Sebep",     value=sebep,                    inline=False)
        await interaction.response.send_message(embed=embed)

    # /kanal kilit-aç
    @kanal.command(name="kilit-aç", description="Kilitli kanalın kilidini açar.")
    @app_commands.describe(kanal="Kilidi açılacak kanal (boş = mevcut)")
    async def kilit_ac(self, interaction: discord.Interaction, kanal: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Kanalları Yönet** yetkisi gereklidir."), ephemeral=True
            )
        target = kanal or interaction.channel
        ow = target.overwrites_for(interaction.guild.default_role)
        ow.send_messages = None
        await target.set_permissions(interaction.guild.default_role, overwrite=ow)

        embed = _emb("🔓 Kilit Açıldı", color=discord.Color.green())
        embed.add_field(name="Kanal",     value=target.mention,           inline=True)
        embed.add_field(name="Moderatör", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        if isinstance(error, app_commands.BotMissingPermissions):
            await send(embed=_emb("❌ Bot Yetki Hatası", "Botun bu işlem için yeterli yetkisi yok."), ephemeral=True)
        else:
            await send(embed=_emb("❌ Hata", str(error)), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelMod(bot))
