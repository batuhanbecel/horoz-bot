import discord
from discord import app_commands
from discord.ext import commands
from database import db
from .._v2 import c_card, c_text, c_section, c_container, c_thumbnail, respond, error_response


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
        thumb = str(interaction.client.user.display_avatar.url)
        if not interaction.user.guild_permissions.manage_messages:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Mesajları Yönet** yetkisi gereklidir.", thumbnail=thumb, color=0xED4245),
                ephemeral=True,
            )
        rows = await db.get_infractions(interaction.guild_id, üye.id)
        if not rows:
            return await respond(interaction,
                c_card("## ✅ Temiz Geçmiş", body=f"{üye.mention} için kayıtlı ihlal bulunamadı.",
                       thumbnail=str(üye.display_avatar.url), color=0x57F287),
                ephemeral=True,
            )

        TYPE_EMOJI = {"warn": "⚠️", "kick": "👢", "ban": "🔨", "mute": "🔇"}
        lines: list[str] = []
        for i, row in enumerate(rows[:10], 1):
            mod = interaction.guild.get_member(row["mod_id"])
            mod_name = mod.display_name if mod else f"ID:{row['mod_id']}"
            emoji = TYPE_EMOJI.get(row["type"], "•")
            lines.append(f"{emoji} **#{i} — {row['type'].upper()}**")
            lines.append(f"📅 {row['created_at'][:10]} · 👮 {mod_name} · 📝 {row['reason'] or 'Belirtilmedi'}")
            lines.append("")

        await respond(interaction, c_card(
            f"## 📋 İhlal Geçmişi — {üye.display_name}",
            body=f"Toplam **{len(rows)}** ihlal\n\n" + "\n".join(lines),
            thumbnail=str(üye.display_avatar.url),
            color=0xE67E22,
        ), ephemeral=True)

    # /ihlal sil
    @ihlal.command(name="sil", description="Bir üyenin tüm ihlallerini temizler.")
    @app_commands.describe(üye="İhlalleri temizlenecek üye")
    async def sil(self, interaction: discord.Interaction, üye: discord.Member):
        thumb = str(interaction.client.user.display_avatar.url)
        if not interaction.user.guild_permissions.administrator:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="Bu komut için **Yönetici** yetkisi gereklidir.", thumbnail=thumb, color=0xED4245),
                ephemeral=True,
            )
        await db.clear_infractions(interaction.guild_id, üye.id)

        await respond(interaction, c_card(
            "## 🗑️ İhlaller Temizlendi",
            body=f"👤 **Üye:** {üye.mention}\n✅ Tüm ihlaller silindi.",
            thumbnail=str(üye.display_avatar.url),
            color=0x57F287,
        ), ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Botun bu işlem için yeterli yetkisi yok." \
            if isinstance(error, app_commands.BotMissingPermissions) else str(error)
        await error_response(interaction, msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(InfractionMod(bot))
