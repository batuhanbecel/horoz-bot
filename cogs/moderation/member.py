import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from database import db
from ._shared import hierarchy_ok, parse_duration
from .._v2 import (
    COLORS, c_card, c_action_card, c_rich_card, c_status_indicator, c_badge, respond, channel_send, error_response,
)


def _no_perm(label: str) -> dict:
    return c_card(
        "## ❌ Yetersiz Yetki",
        body=f"**{label}** yetkisi gereklidir.",
        color=COLORS.DANGER,
    )


def _bot_no_perm(label: str) -> dict:
    return c_card(
        "## ❌ Botun Yetkisi Yok",
        body=f"Botun **{label}** yetkisi bulunmuyor veya hedefin rolü botun rolünden yüksek.",
        color=COLORS.DANGER,
    )


def _hierarchy_err(msg: str) -> dict:
    return c_card("## ❌ Hiyerarşi Hatası", body=msg, color=COLORS.DANGER)


class MemberMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    üye = app_commands.Group(
        name="üye",
        description="Üye yönetim komutları",
        guild_only=True,
    )

    # /üye uyar
    @üye.command(name="uyar", description="Bir üyeye uyarı verir.")
    @app_commands.describe(üye="Uyarılacak üye", sebep="Uyarı sebebi")
    async def uyar(self, interaction: discord.Interaction, üye: discord.Member, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.manage_messages:
            return await respond(interaction, _no_perm("Mesajları Yönet"), ephemeral=True)
        if err := hierarchy_ok(interaction, üye):
            return await respond(interaction, _hierarchy_err(err), ephemeral=True)

        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "warn")
        rows = await db.get_infractions(interaction.guild_id, üye.id)

        await respond(interaction, c_rich_card(
            "⚠️ Uyarı Verildi",
            subtitle=üye.display_name,
            thumbnail=str(üye.display_avatar.url),
            badges=[c_badge("İhlal", "🟡"), c_badge(f"#{len(rows)}", "🔴")],
            body="\n".join([
                c_status_indicator("warn", f"**Üye:** {üye.mention}"),
                c_status_indicator("info", f"**Moderatör:** {interaction.user.mention}"),
                c_status_indicator("warn", f"**Toplam İhlal:** `{len(rows)}`"),
                c_status_indicator("critical", f"**Sebep:** {sebep}"),
            ]),
            footer=f"Sunucu: {interaction.guild.name}",
            color=COLORS.WARNING,
        ))

        # DM bilgilendirme — başarısız olabilir, sessizce geç
        try:
            dm = await üye.create_dm()
            await dm.send(
                f"⚠️ **{interaction.guild.name}** sunucusunda uyarı aldın.\n"
                f"**Sebep:** {sebep}\n"
                f"**Toplam ihlal:** {len(rows)}"
            )
        except Exception:
            pass

    # /üye at
    @üye.command(name="at", description="Bir üyeyi sunucudan atar.")
    @app_commands.describe(üye="Atılacak üye", sebep="Atılma sebebi")
    async def at(self, interaction: discord.Interaction, üye: discord.Member, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.kick_members:
            return await respond(interaction, _no_perm("Üye At"), ephemeral=True)
        if not interaction.guild.me.guild_permissions.kick_members:
            return await respond(interaction, _bot_no_perm("Üye At"), ephemeral=True)
        if err := hierarchy_ok(interaction, üye):
            return await respond(interaction, _hierarchy_err(err), ephemeral=True)

        try:
            await üye.kick(reason=f"{interaction.user}: {sebep}")
        except discord.Forbidden:
            return await respond(interaction, _bot_no_perm("Üye At"), ephemeral=True)
        except discord.HTTPException as ex:
            return await respond(interaction,
                c_card("## ❌ Atma Başarısız", body=f"```{ex}```", color=COLORS.DANGER),
                ephemeral=True,
            )

        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "kick")

        await respond(interaction, c_rich_card(
            "👢 Üye Atıldı",
            subtitle=f"{üye} · `{üye.id}`",
            thumbnail=str(üye.display_avatar.url),
            badges=[c_badge("KICK", "🟠"), c_badge("Moderasyon", "🔴")],
            body="\n".join([
                c_status_indicator("error", f"**Üye:** {üye.mention}"),
                c_status_indicator("info", f"**Moderatör:** {interaction.user.mention}"),
                c_status_indicator("warn", f"**Sebep:** {sebep}"),
            ]),
            footer=f"Sunucu: {interaction.guild.name}",
            color=COLORS.MOD,
        ))

    # /üye yasakla
    @üye.command(name="yasakla", description="Bir üyeyi kalıcı olarak yasaklar.")
    @app_commands.describe(üye="Yasaklanacak üye", sebep="Yasaklama sebebi", mesaj_sil="Kaç günlük mesaj silinsin (0-7)")
    async def yasakla(
        self,
        interaction: discord.Interaction,
        üye: discord.Member,
        sebep: str = "Belirtilmedi",
        mesaj_sil: app_commands.Range[int, 0, 7] = 0,
    ):
        if not interaction.user.guild_permissions.ban_members:
            return await respond(interaction, _no_perm("Üye Yasakla"), ephemeral=True)
        if not interaction.guild.me.guild_permissions.ban_members:
            return await respond(interaction, _bot_no_perm("Üye Yasakla"), ephemeral=True)
        if err := hierarchy_ok(interaction, üye):
            return await respond(interaction, _hierarchy_err(err), ephemeral=True)

        try:
            await üye.ban(
                reason=f"{interaction.user}: {sebep}",
                delete_message_seconds=mesaj_sil * 86400,
            )
        except discord.Forbidden:
            return await respond(interaction, _bot_no_perm("Üye Yasakla"), ephemeral=True)
        except discord.HTTPException as ex:
            return await respond(interaction,
                c_card("## ❌ Yasaklama Başarısız", body=f"```{ex}```", color=COLORS.DANGER),
                ephemeral=True,
            )

        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "ban")

        await respond(interaction, c_rich_card(
            "🔨 Üye Yasaklandı",
            subtitle=f"{üye} · `{üye.id}`",
            thumbnail=str(üye.display_avatar.url),
            badges=[c_badge("BAN", "🔴"), c_badge(f"{mesaj_sil}g silindi", "🟠")],
            body="\n".join([
                c_status_indicator("critical", f"**Üye:** {üye.mention}"),
                c_status_indicator("info", f"**Moderatör:** {interaction.user.mention}"),
                c_status_indicator("warn", f"**Silinen Mesajlar:** `{mesaj_sil}` gün"),
                c_status_indicator("critical", f"**Sebep:** {sebep}"),
            ]),
            footer=f"Sunucu: {interaction.guild.name}",
            color=COLORS.DANGER,
        ))

    # /üye sustur
    @üye.command(name="sustur", description="Bir üyeyi timeout ile susturur.")
    @app_commands.describe(üye="Susturulacak üye", süre="Süre (10m, 2h, 1d)", sebep="Susturma sebebi")
    async def sustur(self, interaction: discord.Interaction, üye: discord.Member, süre: str, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.moderate_members:
            return await respond(interaction, _no_perm("Üyeleri Yönet"), ephemeral=True)
        if not interaction.guild.me.guild_permissions.moderate_members:
            return await respond(interaction, _bot_no_perm("Üyeleri Yönet"), ephemeral=True)
        if err := hierarchy_ok(interaction, üye):
            return await respond(interaction, _hierarchy_err(err), ephemeral=True)

        delta = parse_duration(süre)
        if not delta:
            return await respond(interaction,
                c_card("## ❌ Geçersiz Süre", body="Format: `10m` · `2h` · `1d` · `30s`", color=COLORS.DANGER),
                ephemeral=True,
            )
        if delta > timedelta(days=28):
            return await respond(interaction,
                c_card("## ❌ Hata", body="Maksimum susturma süresi **28 gün**dür.", color=COLORS.DANGER),
                ephemeral=True,
            )

        try:
            await üye.timeout(delta, reason=f"{interaction.user}: {sebep}")
        except discord.Forbidden:
            return await respond(interaction, _bot_no_perm("Üyeleri Yönet"), ephemeral=True)
        except discord.HTTPException as ex:
            return await respond(interaction,
                c_card("## ❌ Susturma Başarısız", body=f"```{ex}```", color=COLORS.DANGER),
                ephemeral=True,
            )

        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "mute")

        await respond(interaction, c_rich_card(
            "🔇 Üye Susturuldu",
            subtitle=üye.display_name,
            thumbnail=str(üye.display_avatar.url),
            badges=[c_badge("TIMEOUT", "🟡"), c_badge(süre, "🟠")],
            body="\n".join([
                c_status_indicator("warn", f"**Üye:** {üye.mention}"),
                c_status_indicator("info", f"**Süre:** `{süre}`"),
                c_status_indicator("info", f"**Moderatör:** {interaction.user.mention}"),
                c_status_indicator("warn", f"**Sebep:** {sebep}"),
            ]),
            footer=f"Sunucu: {interaction.guild.name}",
            color=COLORS.WARNING,
        ))

    # /üye sus-kaldır
    @üye.command(name="sus-kaldır", description="Bir üyenin susturmasını kaldırır.")
    @app_commands.describe(üye="Susturması kaldırılacak üye")
    async def sus_kaldir(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.moderate_members:
            return await respond(interaction, _no_perm("Üyeleri Yönet"), ephemeral=True)
        if not interaction.guild.me.guild_permissions.moderate_members:
            return await respond(interaction, _bot_no_perm("Üyeleri Yönet"), ephemeral=True)
        if not üye.is_timed_out():
            return await respond(interaction,
                c_card("## ⚠️ Hata", body="Bu üye zaten susturulmuş değil.", color=COLORS.WARNING),
                ephemeral=True,
            )

        try:
            await üye.timeout(None, reason=f"{interaction.user}: susturma kaldırıldı")
        except discord.Forbidden:
            return await respond(interaction, _bot_no_perm("Üyeleri Yönet"), ephemeral=True)
        except discord.HTTPException as ex:
            return await respond(interaction,
                c_card("## ❌ Hata", body=f"```{ex}```", color=COLORS.DANGER),
                ephemeral=True,
            )

        await respond(interaction, c_rich_card(
            "🔊 Susturma Kaldırıldı",
            subtitle=üye.display_name,
            thumbnail=str(üye.display_avatar.url),
            badges=[c_badge("UNMUTE", "🟢")],
            body="\n".join([
                c_status_indicator("ok", f"**Üye:** {üye.mention}"),
                c_status_indicator("info", f"**Moderatör:** {interaction.user.mention}"),
            ]),
            color=COLORS.SUCCESS,
        ))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Botun bu işlem için yeterli yetkisi yok." \
            if isinstance(error, app_commands.BotMissingPermissions) else str(error)
        await error_response(interaction, msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberMod(bot))
