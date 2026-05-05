import discord
from discord import app_commands
from discord.ext import commands
from database import db
from ._shared import _emb


class InfractionMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ihlal = app_commands.Group(
        name="ihlal",
        description="İhlal yönetim komutları",
    )

    # /ihlal listele
    @ihlal.command(name="listele", description="Bir üyenin ihlal geçmişini gösterir.")
    @app_commands.describe(üye="İhlalleri görüntülenecek üye")
    async def listele(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Mesajları Yönet** yetkisi gereklidir."), ephemeral=True
            )
        rows = await db.get_infractions(interaction.guild_id, üye.id)
        if not rows:
            return await interaction.response.send_message(
                embed=_emb("✅ Temiz Geçmiş", f"{üye.mention} için kayıtlı ihlal bulunamadı.", discord.Color.green()),
                ephemeral=True,
            )

        embed = discord.Embed(
            title=f"📋 İhlal Geçmişi — {üye.display_name}",
            description=f"Toplam **{len(rows)}** ihlal",
            color=discord.Color.orange(),
        )
        embed.set_thumbnail(url=üye.display_avatar.url)
        embed.set_footer(text="Horoz Bot • Moderasyon")
        embed.timestamp = discord.utils.utcnow()

        TYPE_EMOJI = {"warn": "⚠️", "kick": "👢", "ban": "🔨", "mute": "🔇"}
        for i, row in enumerate(rows[:10], 1):
            mod = interaction.guild.get_member(row["mod_id"])
            mod_name = mod.display_name if mod else f"ID:{row['mod_id']}"
            emoji = TYPE_EMOJI.get(row["type"], "•")
            embed.add_field(
                name=f"{emoji} #{i} — {row['type'].upper()}",
                value=f"**Tarih:** {row['created_at'][:10]}\n**Mod:** {mod_name}\n**Sebep:** {row['reason'] or 'Belirtilmedi'}",
                inline=True,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /ihlal sil
    @ihlal.command(name="sil", description="Bir üyenin tüm ihlallerini temizler.")
    @app_commands.describe(üye="İhlalleri temizlenecek üye")
    async def sil(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "Bu komut için **Yönetici** yetkisi gereklidir."), ephemeral=True
            )
        await db.clear_infractions(interaction.guild_id, üye.id)

        embed = _emb("🗑️ İhlaller Temizlendi", color=discord.Color.green())
        embed.add_field(name="Üye",   value=üye.mention,            inline=True)
        embed.add_field(name="İşlem", value="Tüm ihlaller silindi", inline=True)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        if isinstance(error, app_commands.BotMissingPermissions):
            await send(embed=_emb("❌ Bot Yetki Hatası", "Botun bu işlem için yeterli yetkisi yok."), ephemeral=True)
        else:
            await send(embed=_emb("❌ Hata", str(error)), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(InfractionMod(bot))
