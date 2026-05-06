import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from database import db
from ._shared import hierarchy_ok, parse_duration
from .._v2 import c_text, c_section, c_container, c_thumbnail, respond, channel_send, error_response


class MemberMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    üye = app_commands.Group(
        name="üye",
        description="Üye yönetim komutları",
    )

    # /üye uyar
    @üye.command(name="uyar", description="Bir üyeye uyarı verir.")
    @app_commands.describe(üye="Uyarılacak üye", sebep="Uyarı sebebi")
    async def uyar(self, interaction: discord.Interaction, üye: discord.Member, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.manage_messages:
            return await respond(interaction,
                c_container(c_text("**❌ Yetersiz Yetki**\n\n**Mesajları Yönet** yetkisi gereklidir."), color=0xED4245),
                ephemeral=True,
            )
        if err := hierarchy_ok(interaction, üye):
            return await respond(interaction, c_container(c_text(f"**❌ Hiyerarşi Hatası**\n\n{err}"), color=0xED4245), ephemeral=True)

        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "warn")
        rows = await db.get_infractions(interaction.guild_id, üye.id)

        await respond(interaction,
            c_container(
                c_section(
                    c_text(
                        f"**⚠️ Uyarı Verildi**\n\n"
                        f"👤 **Üye:** {üye.mention}\n"
                        f"👮 **Moderatör:** {interaction.user.mention}\n"
                        f"📊 **Toplam İhlal:** {len(rows)}\n"
                        f"📝 **Sebep:** {sebep}"
                    ),
                    accessory=c_thumbnail(str(üye.display_avatar.url)),
                ),
                color=0xFEE75C,
            ),
        )

        try:
            dm = await üye.create_dm()
            await channel_send(dm,
                c_container(
                    c_text(
                        f"**⚠️ Uyarı — {interaction.guild.name}**\n\n"
                        f"📝 **Sebep:** {sebep}\n"
                        f"📊 **Toplam İhlal:** {len(rows)}"
                    ),
                    color=0xFEE75C,
                ),
            )
        except discord.Forbidden:
            pass

    # /üye at
    @üye.command(name="at", description="Bir üyeyi sunucudan atar.")
    @app_commands.describe(üye="Atılacak üye", sebep="Atılma sebebi")
    async def at(self, interaction: discord.Interaction, üye: discord.Member, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.kick_members:
            return await respond(interaction,
                c_container(c_text("**❌ Yetersiz Yetki**\n\n**Üye At** yetkisi gereklidir."), color=0xED4245),
                ephemeral=True,
            )
        if err := hierarchy_ok(interaction, üye):
            return await respond(interaction, c_container(c_text(f"**❌ Hiyerarşi Hatası**\n\n{err}"), color=0xED4245), ephemeral=True)

        await üye.kick(reason=f"{interaction.user}: {sebep}")
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "kick")

        await respond(interaction,
            c_container(
                c_section(
                    c_text(
                        f"**👢 Üye Atıldı**\n\n"
                        f"👤 **Üye:** {üye} (`{üye.id}`)\n"
                        f"👮 **Moderatör:** {interaction.user.mention}\n"
                        f"📝 **Sebep:** {sebep}"
                    ),
                    accessory=c_thumbnail(str(üye.display_avatar.url)),
                ),
                color=0xE67E22,
            ),
        )

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
            return await respond(interaction,
                c_container(c_text("**❌ Yetersiz Yetki**\n\n**Üye Yasakla** yetkisi gereklidir."), color=0xED4245),
                ephemeral=True,
            )
        if err := hierarchy_ok(interaction, üye):
            return await respond(interaction, c_container(c_text(f"**❌ Hiyerarşi Hatası**\n\n{err}"), color=0xED4245), ephemeral=True)

        await üye.ban(reason=f"{interaction.user}: {sebep}", delete_message_days=mesaj_sil)
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "ban")

        await respond(interaction,
            c_container(
                c_section(
                    c_text(
                        f"**🔨 Üye Yasaklandı**\n\n"
                        f"👤 **Üye:** {üye} (`{üye.id}`)\n"
                        f"👮 **Moderatör:** {interaction.user.mention}\n"
                        f"🗑️ **Silinen Mesajlar:** {mesaj_sil} gün\n"
                        f"📝 **Sebep:** {sebep}"
                    ),
                    accessory=c_thumbnail(str(üye.display_avatar.url)),
                ),
                color=0xED4245,
            ),
        )

    # /üye sustur
    @üye.command(name="sustur", description="Bir üyeyi timeout ile susturur.")
    @app_commands.describe(üye="Susturulacak üye", süre="Süre (10m, 2h, 1d)", sebep="Susturma sebebi")
    async def sustur(self, interaction: discord.Interaction, üye: discord.Member, süre: str, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.moderate_members:
            return await respond(interaction,
                c_container(c_text("**❌ Yetersiz Yetki**\n\n**Üyeleri Yönet** yetkisi gereklidir."), color=0xED4245),
                ephemeral=True,
            )
        if err := hierarchy_ok(interaction, üye):
            return await respond(interaction, c_container(c_text(f"**❌ Hiyerarşi Hatası**\n\n{err}"), color=0xED4245), ephemeral=True)

        delta = parse_duration(süre)
        if not delta:
            return await respond(interaction,
                c_container(c_text("**❌ Geçersiz Süre**\n\nFormat: `10m` · `2h` · `1d` · `30s`"), color=0xED4245),
                ephemeral=True,
            )
        if delta > timedelta(days=28):
            return await respond(interaction,
                c_container(c_text("**❌ Hata**\n\nMaksimum susturma süresi **28 gün**dür."), color=0xED4245),
                ephemeral=True,
            )

        await üye.timeout(delta, reason=f"{interaction.user}: {sebep}")
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "mute")

        await respond(interaction,
            c_container(
                c_section(
                    c_text(
                        f"**🔇 Susturuldu**\n\n"
                        f"👤 **Üye:** {üye.mention}\n"
                        f"⏱️ **Süre:** {süre}\n"
                        f"👮 **Moderatör:** {interaction.user.mention}\n"
                        f"📝 **Sebep:** {sebep}"
                    ),
                    accessory=c_thumbnail(str(üye.display_avatar.url)),
                ),
                color=0xFEE75C,
            ),
        )

    # /üye sus-kaldır
    @üye.command(name="sus-kaldır", description="Bir üyenin susturmasını kaldırır.")
    @app_commands.describe(üye="Susturması kaldırılacak üye")
    async def sus_kaldir(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.moderate_members:
            return await respond(interaction,
                c_container(c_text("**❌ Yetersiz Yetki**\n\n**Üyeleri Yönet** yetkisi gereklidir."), color=0xED4245),
                ephemeral=True,
            )
        if not üye.is_timed_out():
            return await respond(interaction,
                c_container(c_text("**⚠️ Hata**\n\nBu üye zaten susturulmuş değil."), color=0xFEE75C),
                ephemeral=True,
            )
        await üye.timeout(None)

        await respond(interaction,
            c_container(
                c_section(
                    c_text(
                        f"**🔊 Susturma Kaldırıldı**\n\n"
                        f"👤 **Üye:** {üye.mention}\n"
                        f"👮 **Moderatör:** {interaction.user.mention}"
                    ),
                    accessory=c_thumbnail(str(üye.display_avatar.url)),
                ),
                color=0x57F287,
            ),
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Botun bu işlem için yeterli yetkisi yok." \
            if isinstance(error, app_commands.BotMissingPermissions) else str(error)
        await error_response(interaction, msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberMod(bot))
