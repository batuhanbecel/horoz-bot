import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from database import db
from ._shared import _emb, hierarchy_ok, parse_duration


class MemberMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    üye = app_commands.Group(
        name="üye",
        description="Üye yönetim komutları",
        default_member_permissions=None,
    )

    # /üye uyar
    @üye.command(name="uyar", description="Bir üyeye uyarı verir.")
    @app_commands.describe(üye="Uyarılacak üye", sebep="Uyarı sebebi")
    async def uyar(self, interaction: discord.Interaction, üye: discord.Member, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Mesajları Yönet** yetkisi gereklidir."), ephemeral=True
            )
        if err := hierarchy_ok(interaction, üye):
            return await interaction.response.send_message(embed=_emb("❌ Hiyerarşi Hatası", err), ephemeral=True)

        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "warn")
        rows = await db.get_infractions(interaction.guild_id, üye.id)

        embed = _emb("⚠️ Uyarı Verildi", color=discord.Color.yellow())
        embed.add_field(name="Üye",          value=üye.mention,              inline=True)
        embed.add_field(name="Moderatör",    value=interaction.user.mention, inline=True)
        embed.add_field(name="Toplam İhlal", value=str(len(rows)),           inline=True)
        embed.add_field(name="Sebep",        value=sebep,                    inline=False)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed)

        try:
            dm = _emb(f"⚠️ Uyarı — {interaction.guild.name}", color=discord.Color.yellow())
            dm.add_field(name="Sebep",        value=sebep,          inline=False)
            dm.add_field(name="Toplam İhlal", value=str(len(rows)), inline=True)
            await üye.send(embed=dm)
        except discord.Forbidden:
            pass

    # /üye at
    @üye.command(name="at", description="Bir üyeyi sunucudan atar.")
    @app_commands.describe(üye="Atılacak üye", sebep="Atılma sebebi")
    async def at(self, interaction: discord.Interaction, üye: discord.Member, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Üye At** yetkisi gereklidir."), ephemeral=True
            )
        if err := hierarchy_ok(interaction, üye):
            return await interaction.response.send_message(embed=_emb("❌ Hiyerarşi Hatası", err), ephemeral=True)

        await üye.kick(reason=f"{interaction.user}: {sebep}")
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "kick")

        embed = _emb("👢 Üye Atıldı", color=discord.Color.orange())
        embed.add_field(name="Üye",       value=f"{üye} (`{üye.id}`)",  inline=False)
        embed.add_field(name="Moderatör", value=interaction.user.mention, inline=True)
        embed.add_field(name="Sebep",     value=sebep,                    inline=True)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed)

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
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Üye Yasakla** yetkisi gereklidir."), ephemeral=True
            )
        if err := hierarchy_ok(interaction, üye):
            return await interaction.response.send_message(embed=_emb("❌ Hiyerarşi Hatası", err), ephemeral=True)

        await üye.ban(reason=f"{interaction.user}: {sebep}", delete_message_days=mesaj_sil)
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "ban")

        embed = _emb("🔨 Üye Yasaklandı")
        embed.add_field(name="Üye",           value=f"{üye} (`{üye.id}`)",  inline=False)
        embed.add_field(name="Moderatör",     value=interaction.user.mention, inline=True)
        embed.add_field(name="Mesaj Silindi", value=f"{mesaj_sil} gün",       inline=True)
        embed.add_field(name="Sebep",         value=sebep,                    inline=False)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # /üye sustur
    @üye.command(name="sustur", description="Bir üyeyi timeout ile susturur.")
    @app_commands.describe(üye="Susturulacak üye", süre="Süre (10m, 2h, 1d)", sebep="Susturma sebebi")
    async def sustur(self, interaction: discord.Interaction, üye: discord.Member, süre: str, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Üyeleri Yönet** yetkisi gereklidir."), ephemeral=True
            )
        if err := hierarchy_ok(interaction, üye):
            return await interaction.response.send_message(embed=_emb("❌ Hiyerarşi Hatası", err), ephemeral=True)

        delta = parse_duration(süre)
        if not delta:
            return await interaction.response.send_message(
                embed=_emb("❌ Geçersiz Süre", "Format: `10m` · `2h` · `1d` · `30s`"), ephemeral=True
            )
        if delta > timedelta(days=28):
            return await interaction.response.send_message(
                embed=_emb("❌ Hata", "Maksimum susturma süresi **28 gün**dür."), ephemeral=True
            )

        await üye.timeout(delta, reason=f"{interaction.user}: {sebep}")
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "mute")

        embed = _emb("🔇 Susturuldu", color=discord.Color.yellow())
        embed.add_field(name="Üye",       value=üye.mention,              inline=True)
        embed.add_field(name="Süre",      value=süre,                     inline=True)
        embed.add_field(name="Moderatör", value=interaction.user.mention, inline=True)
        embed.add_field(name="Sebep",     value=sebep,                    inline=False)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # /üye sus-kaldır
    @üye.command(name="sus-kaldır", description="Bir üyenin susturmasını kaldırır.")
    @app_commands.describe(üye="Susturması kaldırılacak üye")
    async def sus_kaldir(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Üyeleri Yönet** yetkisi gereklidir."), ephemeral=True
            )
        if not üye.is_timed_out():
            return await interaction.response.send_message(
                embed=_emb("⚠️ Hata", "Bu üye zaten susturulmuş değil."), ephemeral=True
            )
        await üye.timeout(None)

        embed = _emb("🔊 Susturma Kaldırıldı", color=discord.Color.green())
        embed.add_field(name="Üye",       value=üye.mention,              inline=True)
        embed.add_field(name="Moderatör", value=interaction.user.mention, inline=True)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        if isinstance(error, app_commands.BotMissingPermissions):
            await send(embed=_emb("❌ Bot Yetki Hatası", "Botun bu işlem için yeterli yetkisi yok."), ephemeral=True)
        else:
            await send(embed=_emb("❌ Hata", str(error)), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberMod(bot))
