import discord
from discord import app_commands
from discord.ext import commands
from database import db
from .._v2 import c_text, c_section, c_container, c_thumbnail, respond, error_response


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
            return await respond(interaction,
                c_container(c_text("**❌ Yetersiz Yetki**\n\n**Mesajları Yönet** yetkisi gereklidir."), color=0xED4245),
                ephemeral=True,
            )
        rows = await db.get_infractions(interaction.guild_id, üye.id)
        if not rows:
            return await respond(interaction,
                c_container(c_text(f"**✅ Temiz Geçmiş**\n\n{üye.mention} için kayıtlı ihlal bulunamadı."), color=0x57F287),
                ephemeral=True,
            )

        TYPE_EMOJI = {"warn": "⚠️", "kick": "👢", "ban": "🔨", "mute": "🔇"}
        lines = [
            f"**📋 İhlal Geçmişi — {üye.display_name}**",
            f"Toplam **{len(rows)}** ihlal",
            "",
        ]
        for i, row in enumerate(rows[:10], 1):
            mod = interaction.guild.get_member(row["mod_id"])
            mod_name = mod.display_name if mod else f"ID:{row['mod_id']}"
            emoji = TYPE_EMOJI.get(row["type"], "•")
            lines.append(f"{emoji} **#{i} — {row['type'].upper()}**")
            lines.append(f"📅 {row['created_at'][:10]} · 👮 {mod_name} · 📝 {row['reason'] or 'Belirtilmedi'}")
            lines.append("")

        await respond(interaction,
            c_container(
                c_section(
                    c_text("\n".join(lines)),
                    accessory=c_thumbnail(str(üye.display_avatar.url)),
                ),
                color=0xE67E22,
            ),
            ephemeral=True,
        )

    # /ihlal sil
    @ihlal.command(name="sil", description="Bir üyenin tüm ihlallerini temizler.")
    @app_commands.describe(üye="İhlalleri temizlenecek üye")
    async def sil(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            return await respond(interaction,
                c_container(c_text("**❌ Yetersiz Yetki**\n\nBu komut için **Yönetici** yetkisi gereklidir."), color=0xED4245),
                ephemeral=True,
            )
        await db.clear_infractions(interaction.guild_id, üye.id)

        await respond(interaction,
            c_container(
                c_section(
                    c_text(
                        f"**🗑️ İhlaller Temizlendi**\n\n"
                        f"👤 **Üye:** {üye.mention}\n"
                        f"✅ Tüm ihlaller silindi."
                    ),
                    accessory=c_thumbnail(str(üye.display_avatar.url)),
                ),
                color=0x57F287,
            ),
            ephemeral=True,
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Botun bu işlem için yeterli yetkisi yok." \
            if isinstance(error, app_commands.BotMissingPermissions) else str(error)
        await error_response(interaction, msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(InfractionMod(bot))
