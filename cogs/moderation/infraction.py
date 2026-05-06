import discord
from discord import app_commands
from discord.ext import commands
from database import db
from .._v2 import COLORS, c_card, c_list_card, c_action_card, respond, error_response


TYPE_META = {
    "warn": ("⚠️", "UYARI",     COLORS.WARNING),
    "kick": ("👢", "KICK",      COLORS.MOD),
    "ban":  ("🔨", "BAN",       COLORS.DANGER),
    "mute": ("🔇", "MUTE",      COLORS.WARNING),
}


class InfractionMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ihlal = app_commands.Group(
        name="ihlal",
        description="İhlal yönetim komutları",
        guild_only=True,
    )

    # /ihlal listele
    @ihlal.command(name="listele", description="Bir üyenin ihlal geçmişini gösterir.")
    @app_commands.describe(üye="İhlalleri görüntülenecek üye")
    async def listele(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.manage_messages:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Mesajları Yönet** yetkisi gereklidir.", color=COLORS.DANGER),
                ephemeral=True,
            )

        rows = await db.get_infractions(interaction.guild_id, üye.id)
        if not rows:
            return await respond(interaction,
                c_card(
                    "## ✅ Temiz Geçmiş",
                    body=f"{üye.mention} için kayıtlı ihlal bulunamadı.",
                    thumbnail=str(üye.display_avatar.url),
                    color=COLORS.SUCCESS,
                ),
                ephemeral=True,
            )

        lines: list[str] = []
        for i, row in enumerate(rows[:10], 1):
            mod = interaction.guild.get_member(row["mod_id"])
            mod_name = mod.mention if mod else f"`ID:{row['mod_id']}`"
            emoji, label, _ = TYPE_META.get(row["type"], ("•", row["type"].upper(), 0))
            date = row["created_at"][:10]
            reason = row["reason"] or "_Belirtilmedi_"
            lines.append(
                f"{emoji} **#{i:02d} · {label}** · `{date}`\n"
                f"┗ 👮 {mod_name} · 📝 {reason}"
            )

        footer = f"Toplam {len(rows)} ihlal · İlk 10 gösteriliyor" if len(rows) > 10 else f"Toplam {len(rows)} ihlal"

        await respond(interaction, c_list_card(
            f"📋 İhlal Geçmişi — {üye.display_name}",
            rows=lines,
            thumbnail=str(üye.display_avatar.url),
            footer=footer,
            color=COLORS.MOD,
        ), ephemeral=True)

    # /ihlal sil
    @ihlal.command(name="sil", description="Bir üyenin tüm ihlallerini temizler.")
    @app_commands.describe(üye="İhlalleri temizlenecek üye")
    async def sil(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="Bu komut için **Yönetici** yetkisi gereklidir.", color=COLORS.DANGER),
                ephemeral=True,
            )
        rows = await db.get_infractions(interaction.guild_id, üye.id)
        await db.clear_infractions(interaction.guild_id, üye.id)

        await respond(interaction, c_action_card(
            "🗑️ İhlaller Temizlendi",
            target_avatar=str(üye.display_avatar.url),
            fields=[
                ("👤 Üye", üye.mention),
                ("👮 Moderatör", interaction.user.mention),
                ("🧹 Silinen Kayıt", f"`{len(rows)}`"),
            ],
            color=COLORS.SUCCESS,
        ), ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Botun bu işlem için yeterli yetkisi yok." \
            if isinstance(error, app_commands.BotMissingPermissions) else str(error)
        await error_response(interaction, msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(InfractionMod(bot))
