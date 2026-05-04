import discord
from discord import app_commands
from discord.ext import commands
from database import db
import re
from datetime import timedelta


def parse_duration(text: str) -> timedelta | None:
    match = re.fullmatch(r"(\d+)([smhd])", text.strip().lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    return {"s": timedelta(seconds=value), "m": timedelta(minutes=value),
            "h": timedelta(hours=value), "d": timedelta(days=value)}[unit]


def mod_embed(title: str, description: str = "", color: discord.Color = discord.Color.red()) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.timestamp = discord.utils.utcnow()
    return e


def hierarchy_ok(interaction: discord.Interaction, target: discord.Member) -> str | None:
    if target == interaction.user:
        return "Kendinize bu işlemi yapamazsınız."
    if target.top_role >= interaction.user.top_role:
        return "Bu üyeye işlem yapamazsınız (rol hiyerarşisi)."
    if target.top_role >= interaction.guild.me.top_role:
        return "Botun rolü bu üyenin rolünden düşük, işlem yapılamaz."
    return None


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # default_member_permissions=None → komutlar tüm üyelere görünür,
    # yetki kontrolü her komutun içinde manuel yapılır.
    mod = app_commands.Group(
        name="moderatör",
        description="Moderasyon komutları",
        default_member_permissions=None,
    )

    # /moderatör temizle
    @mod.command(name="temizle", description="Belirtilen sayıda mesajı siler.")
    @app_commands.describe(miktar="Silinecek mesaj sayısı (1-100)")
    async def temizle(self, interaction: discord.Interaction, miktar: app_commands.Range[int, 1, 100]):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komut için **Mesajları Yönet** yetkisi gereklidir."),
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=miktar)
        await interaction.followup.send(
            embed=mod_embed("Temizlendi", f"{len(deleted)} mesaj silindi.", discord.Color.green()),
            ephemeral=True,
        )

    # /moderatör uyar
    @mod.command(name="uyar", description="Bir üyeye uyarı verir (infraction kaydı oluşturur).")
    @app_commands.describe(üye="Uyarılacak üye", sebep="Uyarı sebebi")
    async def uyar(self, interaction: discord.Interaction, üye: discord.Member, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komut için **Mesajları Yönet** yetkisi gereklidir."),
                ephemeral=True,
            )
        err = hierarchy_ok(interaction, üye)
        if err:
            return await interaction.response.send_message(embed=mod_embed("Hata", err), ephemeral=True)

        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "warn")
        rows = await db.get_infractions(interaction.guild_id, üye.id)
        await interaction.response.send_message(
            embed=mod_embed(
                "Uyarıldı",
                f"{üye.mention} uyarıldı. Toplam ihlal: **{len(rows)}**\n**Sebep:** {sebep}",
                discord.Color.yellow(),
            )
        )
        try:
            await üye.send(
                embed=mod_embed(
                    f"⚠️ {interaction.guild.name} sunucusunda uyarı aldınız",
                    f"**Sebep:** {sebep}\nToplam ihlal sayınız: **{len(rows)}**",
                    discord.Color.yellow(),
                )
            )
        except discord.Forbidden:
            pass

    # /moderatör at
    @mod.command(name="at", description="Bir üyeyi sunucudan atar.")
    @app_commands.describe(üye="Atılacak üye", sebep="Atılma sebebi")
    async def at(self, interaction: discord.Interaction, üye: discord.Member, sebep: str = "Belirtilmedi"):
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komut için **Üye At** yetkisi gereklidir."),
                ephemeral=True,
            )
        err = hierarchy_ok(interaction, üye)
        if err:
            return await interaction.response.send_message(embed=mod_embed("Hata", err), ephemeral=True)

        await üye.kick(reason=f"{interaction.user}: {sebep}")
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "kick")
        await interaction.response.send_message(
            embed=mod_embed("Atıldı", f"{üye.mention} sunucudan atıldı.\n**Sebep:** {sebep}", discord.Color.orange())
        )

    # /moderatör yasakla
    @mod.command(name="yasakla", description="Bir üyeyi kalıcı olarak yasaklar.")
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
                embed=mod_embed("Yetki Hatası", "Bu komut için **Üye Yasakla** yetkisi gereklidir."),
                ephemeral=True,
            )
        err = hierarchy_ok(interaction, üye)
        if err:
            return await interaction.response.send_message(embed=mod_embed("Hata", err), ephemeral=True)

        await üye.ban(reason=f"{interaction.user}: {sebep}", delete_message_days=mesaj_sil)
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "ban")
        await interaction.response.send_message(
            embed=mod_embed("Yasaklandı", f"{üye.mention} yasaklandı.\n**Sebep:** {sebep}")
        )

    # /moderatör sustur
    @mod.command(name="sustur", description="Bir üyeyi timeout ile susturur.")
    @app_commands.describe(üye="Susturulacak üye", süre="Süre (örn: 10m, 2h, 1d)", sebep="Susturma sebebi")
    async def sustur(
        self,
        interaction: discord.Interaction,
        üye: discord.Member,
        süre: str,
        sebep: str = "Belirtilmedi",
    ):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komut için **Üyeleri Yönet** yetkisi gereklidir."),
                ephemeral=True,
            )
        err = hierarchy_ok(interaction, üye)
        if err:
            return await interaction.response.send_message(embed=mod_embed("Hata", err), ephemeral=True)

        delta = parse_duration(süre)
        if not delta:
            return await interaction.response.send_message(
                embed=mod_embed("Hata", "Geçersiz süre. Örnek: `10m`, `2h`, `1d`"), ephemeral=True
            )
        if delta > timedelta(days=28):
            return await interaction.response.send_message(
                embed=mod_embed("Hata", "Maksimum susturma süresi 28 gündür."), ephemeral=True
            )

        await üye.timeout(delta, reason=f"{interaction.user}: {sebep}")
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "mute")
        await interaction.response.send_message(
            embed=mod_embed(
                "Susturuldu",
                f"{üye.mention} **{süre}** süreyle susturuldu.\n**Sebep:** {sebep}",
                discord.Color.yellow(),
            )
        )

    # /moderatör sustur-kaldır
    @mod.command(name="sustur-kaldır", description="Bir üyenin susturmasını kaldırır.")
    @app_commands.describe(üye="Susturması kaldırılacak üye")
    async def sustu_kaldir(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komut için **Üyeleri Yönet** yetkisi gereklidir."),
                ephemeral=True,
            )
        if not üye.is_timed_out():
            return await interaction.response.send_message(
                embed=mod_embed("Hata", "Bu üye zaten susturulmuş değil."), ephemeral=True
            )
        await üye.timeout(None)
        await interaction.response.send_message(
            embed=mod_embed("Susturma Kaldırıldı", f"{üye.mention} artık konuşabilir.", discord.Color.green())
        )

    # /moderatör yavaşmod
    @mod.command(name="yavaşmod", description="Kanalda yavaş mod süresini ayarlar.")
    @app_commands.describe(saniye="Mesajlar arası bekleme süresi (0 = kapalı, max 21600)", kanal="Kanal (boş = mevcut kanal)")
    async def yavaşmod(
        self,
        interaction: discord.Interaction,
        saniye: app_commands.Range[int, 0, 21600],
        kanal: discord.TextChannel = None,
    ):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komut için **Kanalları Yönet** yetkisi gereklidir."),
                ephemeral=True,
            )
        target = kanal or interaction.channel
        await target.edit(slowmode_delay=saniye)
        desc = f"{target.mention} kanalında yavaş mod {'**%d saniye** olarak ayarlandı.' % saniye if saniye else 'kapatıldı.'}"
        color = discord.Color.green() if saniye == 0 else discord.Color.orange()
        await interaction.response.send_message(embed=mod_embed("Yavaş Mod", desc, color), ephemeral=True)

    # /moderatör kilitle
    @mod.command(name="kilitle", description="Kanalı kilitler, üyeler mesaj gönderemez.")
    @app_commands.describe(kanal="Kilitlenecek kanal (boş = mevcut kanal)", sebep="Kilitleme sebebi")
    async def kilitle(
        self,
        interaction: discord.Interaction,
        kanal: discord.TextChannel = None,
        sebep: str = "Belirtilmedi",
    ):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komut için **Kanalları Yönet** yetkisi gereklidir."),
                ephemeral=True,
            )
        target = kanal or interaction.channel
        overwrite = target.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await target.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"{interaction.user}: {sebep}")
        await interaction.response.send_message(
            embed=mod_embed("🔒 Kanal Kilitlendi", f"{target.mention} kilitlendi.\n**Sebep:** {sebep}")
        )

    # /moderatör kilidi-kaldır
    @mod.command(name="kilidi-kaldır", description="Kilitli kanalın kilidini açar.")
    @app_commands.describe(kanal="Kilidi açılacak kanal (boş = mevcut kanal)")
    async def kilidi_kaldir(self, interaction: discord.Interaction, kanal: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komut için **Kanalları Yönet** yetkisi gereklidir."),
                ephemeral=True,
            )
        target = kanal or interaction.channel
        overwrite = target.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await target.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(
            embed=mod_embed("🔓 Kanal Kilidi Açıldı", f"{target.mention} artık açık.", discord.Color.green())
        )

    # /moderatör ihlaller
    @mod.command(name="ihlaller", description="Bir üyenin ihlal geçmişini gösterir.")
    @app_commands.describe(üye="İhlalleri görüntülenecek üye")
    async def ihlaller(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komut için **Mesajları Yönet** yetkisi gereklidir."),
                ephemeral=True,
            )
        rows = await db.get_infractions(interaction.guild_id, üye.id)
        if not rows:
            return await interaction.response.send_message(
                embed=mod_embed("İhlaller", f"{üye.mention} için kayıtlı ihlal yok.", discord.Color.green()),
                ephemeral=True,
            )
        embed = discord.Embed(
            title=f"{üye.display_name} — İhlaller ({len(rows)})",
            color=discord.Color.orange(),
        )
        for i, row in enumerate(rows[:10], 1):
            mod = interaction.guild.get_member(row["mod_id"])
            mod_name = mod.display_name if mod else f"ID:{row['mod_id']}"
            embed.add_field(
                name=f"#{i} — {row['type'].upper()} ({row['created_at'][:10]})",
                value=f"**Mod:** {mod_name}\n**Sebep:** {row['reason'] or 'Yok'}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /moderatör ihlal-temizle
    @mod.command(name="ihlal-temizle", description="Bir üyenin tüm ihlallerini temizler.")
    @app_commands.describe(üye="İhlalleri temizlenecek üye")
    async def ihlal_temizle(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komut için **Yönetici** yetkisi gereklidir."),
                ephemeral=True,
            )
        await db.clear_infractions(interaction.guild_id, üye.id)
        await interaction.response.send_message(
            embed=mod_embed("Temizlendi", f"{üye.mention} tüm ihlalleri silindi.", discord.Color.green()),
            ephemeral=True,
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        if isinstance(error, app_commands.BotMissingPermissions):
            await send(embed=mod_embed("Bot Yetki Hatası", "Botun bu işlem için yeterli yetkisi yok."), ephemeral=True)
        else:
            await send(embed=mod_embed("Hata", str(error)), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
