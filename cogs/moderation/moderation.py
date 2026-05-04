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
    v, u = int(match.group(1)), match.group(2)
    return {"s": timedelta(seconds=v), "m": timedelta(minutes=v),
            "h": timedelta(hours=v),   "d": timedelta(days=v)}[u]


def _emb(title: str, desc: str = "", color: discord.Color = discord.Color.red()) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text="Horoz Bot • Moderasyon")
    e.timestamp = discord.utils.utcnow()
    return e


def hierarchy_ok(interaction: discord.Interaction, target: discord.Member) -> str | None:
    if target == interaction.user:
        return "Kendinize bu işlemi yapamazsınız."
    if target.top_role >= interaction.user.top_role:
        return "Bu üyenin rolü sizin rolünüzden yüksek veya eşit."
    if target.top_role >= interaction.guild.me.top_role:
        return "Bu üyenin rolü botun rolünden yüksek veya eşit."
    return None


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    mod = app_commands.Group(
        name="moderatör",
        description="Moderasyon komutları",
        default_member_permissions=None,   # tüm üyelere görünür, yetki içeride kontrol edilir
    )

    # /moderatör temizle
    @mod.command(name="temizle", description="Belirtilen sayıda mesajı siler.")
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

    # /moderatör uyar
    @mod.command(name="uyar", description="Bir üyeye uyarı verir.")
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
        embed.add_field(name="Üye",          value=üye.mention,         inline=True)
        embed.add_field(name="Moderatör",    value=interaction.user.mention, inline=True)
        embed.add_field(name="Toplam İhlal", value=str(len(rows)),       inline=True)
        embed.add_field(name="Sebep",        value=sebep,                inline=False)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed)

        try:
            dm = _emb(f"⚠️ Uyarı — {interaction.guild.name}", color=discord.Color.yellow())
            dm.add_field(name="Sebep",        value=sebep,          inline=False)
            dm.add_field(name="Toplam İhlal", value=str(len(rows)), inline=True)
            await üye.send(embed=dm)
        except discord.Forbidden:
            pass

    # /moderatör at
    @mod.command(name="at", description="Bir üyeyi sunucudan atar.")
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
        embed.add_field(name="Üye",       value=f"{üye} (`{üye.id}`)", inline=False)
        embed.add_field(name="Moderatör", value=interaction.user.mention, inline=True)
        embed.add_field(name="Sebep",     value=sebep,                   inline=True)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed)

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
                embed=_emb("❌ Yetersiz Yetki", "**Üye Yasakla** yetkisi gereklidir."), ephemeral=True
            )
        if err := hierarchy_ok(interaction, üye):
            return await interaction.response.send_message(embed=_emb("❌ Hiyerarşi Hatası", err), ephemeral=True)

        await üye.ban(reason=f"{interaction.user}: {sebep}", delete_message_days=mesaj_sil)
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "ban")

        embed = _emb("🔨 Üye Yasaklandı")
        embed.add_field(name="Üye",           value=f"{üye} (`{üye.id}`)", inline=False)
        embed.add_field(name="Moderatör",     value=interaction.user.mention, inline=True)
        embed.add_field(name="Mesaj Silindi", value=f"{mesaj_sil} gün",        inline=True)
        embed.add_field(name="Sebep",         value=sebep,                    inline=False)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # /moderatör sustur
    @mod.command(name="sustur", description="Bir üyeyi timeout ile susturur.")
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
        embed.add_field(name="Üye",       value=üye.mention,             inline=True)
        embed.add_field(name="Süre",      value=süre,                    inline=True)
        embed.add_field(name="Moderatör", value=interaction.user.mention, inline=True)
        embed.add_field(name="Sebep",     value=sebep,                   inline=False)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # /moderatör sus-kaldır
    @mod.command(name="sus-kaldır", description="Bir üyenin susturmasını kaldırır.")
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
        embed.add_field(name="Üye",       value=üye.mention,             inline=True)
        embed.add_field(name="Moderatör", value=interaction.user.mention, inline=True)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # /moderatör yavaşmod
    @mod.command(name="yavaşmod", description="Kanal yavaş modunu ayarlar (0 = kapalı).")
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

    # /moderatör kilitle
    @mod.command(name="kilitle", description="Kanalı kilitler, üyeler mesaj gönderemez.")
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
        embed.add_field(name="Kanal",     value=target.mention,          inline=True)
        embed.add_field(name="Moderatör", value=interaction.user.mention, inline=True)
        embed.add_field(name="Sebep",     value=sebep,                   inline=False)
        await interaction.response.send_message(embed=embed)

    # /moderatör kilit-aç
    @mod.command(name="kilit-aç", description="Kilitli kanalın kilidini açar.")
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
        embed.add_field(name="Kanal",     value=target.mention,          inline=True)
        embed.add_field(name="Moderatör", value=interaction.user.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    # /moderatör ihlaller
    @mod.command(name="ihlaller", description="Bir üyenin ihlal geçmişini gösterir.")
    @app_commands.describe(üye="İhlalleri görüntülenecek üye")
    async def ihlaller(self, interaction: discord.Interaction, üye: discord.Member):
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
            emoji    = TYPE_EMOJI.get(row["type"], "•")
            embed.add_field(
                name=f"{emoji} #{i} — {row['type'].upper()}",
                value=f"**Tarih:** {row['created_at'][:10]}\n**Mod:** {mod_name}\n**Sebep:** {row['reason'] or 'Belirtilmedi'}",
                inline=True,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /moderatör ihlal-sil
    @mod.command(name="ihlal-sil", description="Bir üyenin tüm ihlallerini temizler.")
    @app_commands.describe(üye="İhlalleri temizlenecek üye")
    async def ihlal_sil(self, interaction: discord.Interaction, üye: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "Bu komut için **Yönetici** yetkisi gereklidir."), ephemeral=True
            )
        await db.clear_infractions(interaction.guild_id, üye.id)
        embed = _emb("🗑️ İhlaller Temizlendi", color=discord.Color.green())
        embed.add_field(name="Üye",    value=üye.mention,              inline=True)
        embed.add_field(name="İşlem",  value="Tüm ihlaller silindi",   inline=True)
        embed.set_thumbnail(url=üye.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        if isinstance(error, app_commands.BotMissingPermissions):
            await send(embed=_emb("❌ Bot Yetki Hatası", "Botun bu işlem için yeterli yetkisi yok."), ephemeral=True)
        else:
            await send(embed=_emb("❌ Hata", str(error)), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
