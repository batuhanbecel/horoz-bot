import discord
from discord import app_commands
from discord.ext import commands
from datetime import timezone, datetime
import asyncio


RENK_MAP: dict[str, discord.Color] = {
    "mavi":    discord.Color.blue(),
    "yesil":   discord.Color.green(),
    "kirmizi": discord.Color.red(),
    "altin":   discord.Color.gold(),
    "mor":     discord.Color.purple(),
    "turuncu": discord.Color.orange(),
    "pembe":   discord.Color.magenta(),
}


def util_embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.timestamp = discord.utils.utcnow()
    return e


# ── Modaller ───────────────────────────────────────────────────────────────────

class MesajModal(discord.ui.Modal, title="Mesaj Gönder"):
    içerik = discord.ui.TextInput(
        label="Mesaj İçeriği",
        style=discord.TextStyle.paragraph,
        placeholder="Göndermek istediğin mesajı buraya yaz...",
        max_length=2000,
    )

    def __init__(self, kanal: discord.TextChannel):
        super().__init__()
        self.kanal = kanal

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.kanal.send(self.içerik.value)
            await interaction.response.send_message(
                embed=util_embed("Mesaj Gönderildi", f"{self.kanal.mention} kanalına mesaj gönderildi.", discord.Color.green()),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=util_embed("Hata", f"{self.kanal.mention} kanalına yazma iznim yok.", discord.Color.red()),
                ephemeral=True,
            )


class EmbedModal(discord.ui.Modal, title="Embed Mesaj Gönder"):
    başlık_f = discord.ui.TextInput(
        label="Başlık",
        placeholder="Embed başlığı",
        max_length=256,
    )
    içerik_f = discord.ui.TextInput(
        label="İçerik",
        style=discord.TextStyle.paragraph,
        placeholder="Embed metni...",
        max_length=4000,
    )

    def __init__(self, kanal: discord.TextChannel, renk: discord.Color):
        super().__init__()
        self.kanal = kanal
        self.renk = renk

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=self.başlık_f.value,
            description=self.içerik_f.value,
            color=self.renk,
        )
        embed.set_footer(
            text=f"Gönderen: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        embed.timestamp = discord.utils.utcnow()
        try:
            await self.kanal.send(embed=embed)
            await interaction.response.send_message(
                embed=util_embed("Embed Gönderildi", f"{self.kanal.mention} kanalına embed gönderildi.", discord.Color.green()),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=util_embed("Hata", f"{self.kanal.mention} kanalına yazma iznim yok.", discord.Color.red()),
                ephemeral=True,
            )


class DuyuruModal(discord.ui.Modal, title="Duyuru Gönder"):
    içerik_f = discord.ui.TextInput(
        label="Duyuru İçeriği",
        style=discord.TextStyle.paragraph,
        placeholder="Duyuru metni...",
        max_length=2000,
    )

    def __init__(self, kanal: discord.TextChannel, ping: str):
        super().__init__()
        self.kanal = kanal
        self.ping = ping  # "@everyone", "@here" veya ""

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📣 Duyuru",
            description=self.içerik_f.value,
            color=discord.Color.gold(),
        )
        embed.set_footer(
            text=f"Duyuran: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        embed.timestamp = discord.utils.utcnow()
        try:
            await self.kanal.send(content=self.ping or None, embed=embed)
            await interaction.response.send_message(
                embed=util_embed("Duyuru Gönderildi", f"{self.kanal.mention} kanalına duyuru gönderildi.", discord.Color.green()),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=util_embed("Hata", f"{self.kanal.mention} kanalına yazma iznim yok.", discord.Color.red()),
                ephemeral=True,
            )


# ── Utility Cog ───────────────────────────────────────────────────────────────

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._start_time = datetime.now(timezone.utc)

    # /yardım
    @app_commands.command(name="yardım", description="Tüm komutları listeler.")
    async def yardım(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🐓 Horoz Bot — Komut Listesi", color=discord.Color.blurple())
        embed.add_field(
            name="🛡️ /moderatör",
            value="`temizle` `uyar` `at` `yasakla` `sustur` `sustur-kaldır`\n`yavaşmod` `kilitle` `kilidi-kaldır` `ihlaller` `ihlal-temizle`",
            inline=False,
        )
        embed.add_field(
            name="🎵 /müzik",
            value="`çal` `ara` `atla` `duraklat` `devam` `dur`\n`ses` `sıra` `sıra-temizle` `karıştır` `döngü` `şimdi-çalıyor`",
            inline=False,
        )
        embed.add_field(
            name="🎉 Eğlence",
            value="`/yazıtura` `/zar` `/8top` `/anket` `/etkinlik`",
            inline=False,
        )
        embed.add_field(
            name="😀 Emoji & Sticker",
            value="`/emoji-çal` `/emoji-otomatik`\nSağ tık → `Emojileri Ekle` | `Sticker'ı Ekle`",
            inline=False,
        )
        embed.add_field(
            name="⚙️ Özel Komutlar",
            value="`/komutyarat` `/komutlistele` `/komutsil` `/komut`",
            inline=False,
        )
        embed.add_field(
            name="📢 Yönetim & Yayın",
            value="`/mesaj-gönder` `/embed-gönder` `/duyuru` `/komuttazele`",
            inline=False,
        )
        embed.add_field(
            name="ℹ️ Araçlar",
            value="`/yardım` `/ping` `/hatırlat` `/kullanici-bilgi` `/sunucu-bilgi` `/avatar` `/bot-bilgi`",
            inline=False,
        )
        embed.set_footer(text="Horoz Bot | Tüm komutlar slash (/) ile kullanılır.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /ping
    @app_commands.command(name="ping", description="Botun gecikme süresini gösterir.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        color = discord.Color.green() if latency < 100 else discord.Color.orange() if latency < 200 else discord.Color.red()
        embed = util_embed("🏓 Pong!", f"WebSocket gecikmesi: **{latency}ms**", color)
        await interaction.response.send_message(embed=embed)

    # /avatar
    @app_commands.command(name="avatar", description="Bir kullanıcının avatarını gösterir.")
    @app_commands.describe(üye="Avatarı gösterilecek üye (boş bırakılırsa kendiniz)")
    async def avatar(self, interaction: discord.Interaction, üye: discord.Member = None):
        target = üye or interaction.user
        embed = discord.Embed(title=f"{target.display_name} — Avatar", color=discord.Color.blurple())
        embed.set_image(url=target.display_avatar.with_size(1024).url)
        links = (
            f"[PNG]({target.display_avatar.with_format('png').url}) | "
            f"[JPG]({target.display_avatar.with_format('jpg').url}) | "
            f"[WEBP]({target.display_avatar.with_format('webp').url})"
        )
        embed.description = links
        await interaction.response.send_message(embed=embed)

    # /bot-bilgi
    @app_commands.command(name="bot-bilgi", description="Bot hakkında istatistiksel bilgi verir.")
    async def bilgi_bot(self, interaction: discord.Interaction):
        uptime_delta = datetime.now(timezone.utc) - self._start_time
        hours, rem = divmod(int(uptime_delta.total_seconds()), 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{hours}s {minutes}d {seconds}sn"

        embed = discord.Embed(title="🐓 Horoz Bot — Bilgi", color=discord.Color.blurple())
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.add_field(name="Sunucu Sayısı", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Toplam Üye", value=str(sum(g.member_count for g in self.bot.guilds)), inline=True)
        embed.add_field(name="Gecikme", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Çalışma Süresi", value=uptime_str, inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="GitHub", value="[batuhanbecel/horoz-bot](https://github.com/batuhanbecel/horoz-bot)", inline=True)
        await interaction.response.send_message(embed=embed)

    # /kullanici-bilgi
    @app_commands.command(name="kullanici-bilgi", description="Bir kullanıcı hakkında bilgi verir.")
    @app_commands.describe(üye="Bilgi alınacak üye (boş bırakılırsa kendiniz)")
    async def kullanici_bilgi(self, interaction: discord.Interaction, üye: discord.Member = None):
        target = üye or interaction.user
        embed = discord.Embed(
            title=f"{target.display_name} — Kullanıcı Bilgisi",
            color=target.color if target.color != discord.Color.default() else discord.Color.blurple(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Kullanıcı Adı", value=str(target), inline=True)
        embed.add_field(name="ID", value=str(target.id), inline=True)
        embed.add_field(name="Bot mu?", value="Evet" if target.bot else "Hayır", inline=True)
        created = target.created_at.replace(tzinfo=timezone.utc)
        embed.add_field(name="Hesap Oluşturulma", value=f"<t:{int(created.timestamp())}:R>", inline=True)
        if isinstance(target, discord.Member):
            joined = target.joined_at.replace(tzinfo=timezone.utc)
            embed.add_field(name="Sunucuya Katılma", value=f"<t:{int(joined.timestamp())}:R>", inline=True)
            roles = [r.mention for r in target.roles if r.name != "@everyone"]
            embed.add_field(name=f"Roller ({len(roles)})", value=", ".join(roles[:10]) or "Yok", inline=False)
        await interaction.response.send_message(embed=embed)

    # /sunucu-bilgi
    @app_commands.command(name="sunucu-bilgi", description="Sunucu hakkında bilgi verir.")
    async def sunucu_bilgi(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"{guild.name} — Sunucu Bilgisi", color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        created = guild.created_at.replace(tzinfo=timezone.utc)
        embed.add_field(name="Sahip", value=guild.owner.mention if guild.owner else "Bilinmiyor", inline=True)
        embed.add_field(name="ID", value=str(guild.id), inline=True)
        embed.add_field(name="Oluşturulma", value=f"<t:{int(created.timestamp())}:R>", inline=True)
        embed.add_field(name="Üye Sayısı", value=str(guild.member_count), inline=True)
        embed.add_field(name="Kanal Sayısı", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Rol Sayısı", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Boost", value=f"Seviye {guild.premium_tier} ({guild.premium_subscription_count} boost)", inline=True)
        embed.add_field(name="Doğrulama", value=str(guild.verification_level).title(), inline=True)
        embed.add_field(name="Kanallar", value=f"💬 {len(guild.text_channels)} metin | 🔊 {len(guild.voice_channels)} ses", inline=True)
        await interaction.response.send_message(embed=embed)

    # /mesaj-gönder
    @app_commands.command(name="mesaj-gönder", description="Seçilen kanala botun ağzından mesaj gönderir.")
    @app_commands.describe(kanal="Mesajın gönderileceği kanal")
    async def mesaj_gonder(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=util_embed("Yetki Hatası", "Bu komut için **Mesajları Yönet** yetkisi gereklidir.", discord.Color.red()),
                ephemeral=True,
            )
        await interaction.response.send_modal(MesajModal(kanal))

    # /embed-gönder
    @app_commands.command(name="embed-gönder", description="Seçilen kanala embed mesaj gönderir.")
    @app_commands.describe(kanal="Mesajın gönderileceği kanal", renk="Embed kenar rengi")
    @app_commands.choices(renk=[
        app_commands.Choice(name="Mavi",    value="mavi"),
        app_commands.Choice(name="Yeşil",   value="yesil"),
        app_commands.Choice(name="Kırmızı", value="kirmizi"),
        app_commands.Choice(name="Altın",   value="altin"),
        app_commands.Choice(name="Mor",     value="mor"),
        app_commands.Choice(name="Turuncu", value="turuncu"),
        app_commands.Choice(name="Pembe",   value="pembe"),
    ])
    async def embed_gonder(
        self,
        interaction: discord.Interaction,
        kanal: discord.TextChannel,
        renk: str = "mavi",
    ):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=util_embed("Yetki Hatası", "Bu komut için **Mesajları Yönet** yetkisi gereklidir.", discord.Color.red()),
                ephemeral=True,
            )
        color = RENK_MAP.get(renk, discord.Color.blue())
        await interaction.response.send_modal(EmbedModal(kanal, color))

    # /duyuru
    @app_commands.command(name="duyuru", description="Seçilen kanala duyuru gönderir.")
    @app_commands.describe(kanal="Duyurunun gönderileceği kanal", ping="Ping türü")
    @app_commands.choices(ping=[
        app_commands.Choice(name="@everyone",      value="@everyone"),
        app_commands.Choice(name="@here",           value="@here"),
        app_commands.Choice(name="Ping Yok",        value=""),
    ])
    async def duyuru(
        self,
        interaction: discord.Interaction,
        kanal: discord.TextChannel,
        ping: str = "",
    ):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=util_embed("Yetki Hatası", "Bu komut için **Mesajları Yönet** yetkisi gereklidir.", discord.Color.red()),
                ephemeral=True,
            )
        await interaction.response.send_modal(DuyuruModal(kanal, ping))

    # /hatırlat
    @app_commands.command(name="hatırlat", description="Belirlenen dakika sonra DM ile hatırlatma gönderir.")
    @app_commands.describe(dakika="Kaç dakika sonra hatırlatılsın (1-1440)", mesaj="Hatırlatma mesajı")
    async def hatirlat(
        self,
        interaction: discord.Interaction,
        dakika: app_commands.Range[int, 1, 1440],
        mesaj: str = "Hatırlatma!",
    ):
        await interaction.response.send_message(
            embed=util_embed(
                "⏰ Hatırlatma Kuruldu",
                f"**{dakika} dakika** sonra DM olarak hatırlatılacaksın.\n> {mesaj}",
                discord.Color.green(),
            ),
            ephemeral=True,
        )

        async def _remind():
            await asyncio.sleep(dakika * 60)
            try:
                embed = util_embed(
                    "⏰ Hatırlatma!",
                    f"{mesaj}\n\n*{dakika} dakika önce **{interaction.guild.name}** sunucusunda ayarlandı.*",
                    discord.Color.gold(),
                )
                await interaction.user.send(embed=embed)
            except discord.Forbidden:
                pass

        asyncio.create_task(_remind())

    # /komuttazele
    @app_commands.command(name="komuttazele", description="Slash komutlarını Discord ile senkronize eder (eski komutları siler).")
    @app_commands.checks.has_permissions(administrator=True)
    async def komuttazele(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.bot.tree.clear_commands(guild=interaction.guild)
        await self.bot.tree.sync(guild=interaction.guild)
        synced = await self.bot.tree.sync()
        await interaction.followup.send(
            embed=util_embed(
                "Komutlar Tazelendi",
                f"**{len(synced)}** global slash komutu senkronize edildi.\nSunucuya özel eski komutlar temizlendi.",
                discord.Color.green(),
            ),
            ephemeral=True,
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "Bu komutu kullanmak için **Yönetici** yetkisine ihtiyacınız var."
        else:
            msg = str(error)
        if interaction.response.is_done():
            await interaction.followup.send(embed=util_embed("Yetki Hatası", msg, discord.Color.red()), ephemeral=True)
        else:
            await interaction.response.send_message(embed=util_embed("Yetki Hatası", msg, discord.Color.red()), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
