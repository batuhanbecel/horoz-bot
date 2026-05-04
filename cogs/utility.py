import discord
from discord import app_commands
from discord.ext import commands
from datetime import timezone, datetime


def util_embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


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
            value="`temizle` `at` `yasakla` `sustur` `sustu-kaldır` `ihlaller` `ihlal-temizle`",
            inline=False,
        )
        embed.add_field(
            name="🎵 /müzik",
            value="`çal` `ara` `atla` `duraklat` `devam` `dur` `ses` `sıra` `sıra-temizle` `döngü`",
            inline=False,
        )
        embed.add_field(
            name="🎉 Eğlence",
            value="`/yazıtura` `/zar` `/anket` `/etkinlik`",
            inline=False,
        )
        embed.add_field(
            name="⚙️ Özel Komutlar",
            value="`/komutyarat` `/komutlistele` `/komutsil` `/komut`",
            inline=False,
        )
        embed.add_field(
            name="ℹ️ Araçlar",
            value="`/yardım` `/ping` `/kullanici-bilgi` `/sunucu-bilgi` `/avatar` `/bot-bilgi`",
            inline=False,
        )
        embed.add_field(
            name="🔧 Yönetim",
            value="`/komuttazele`",
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
        links = f"[PNG]({target.display_avatar.with_format('png').url}) | [JPG]({target.display_avatar.with_format('jpg').url}) | [WEBP]({target.display_avatar.with_format('webp').url})"
        embed.description = links
        await interaction.response.send_message(embed=embed)

    # /bot-bilgi
    @app_commands.command(name="bot-bilgi", description="Bot hakkında istatistiksel bilgi verir.")
    async def bot_bilgi(self, interaction: discord.Interaction):
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
            embed.add_field(
                name=f"Roller ({len(roles)})",
                value=", ".join(roles[:10]) or "Yok",
                inline=False,
            )
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
        embed.add_field(
            name="Boost",
            value=f"Seviye {guild.premium_tier} ({guild.premium_subscription_count} boost)",
            inline=True,
        )
        embed.add_field(name="Doğrulama", value=str(guild.verification_level).title(), inline=True)
        embed.add_field(
            name="Kanallar",
            value=f"💬 {len(guild.text_channels)} metin | 🔊 {len(guild.voice_channels)} ses",
            inline=True,
        )
        await interaction.response.send_message(embed=embed)

    # /komuttazele
    @app_commands.command(name="komuttazele", description="Slash komutlarını Discord ile senkronize eder.")
    @app_commands.checks.has_permissions(administrator=True)
    async def komuttazele(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        synced = await self.bot.tree.sync()
        await interaction.followup.send(
            embed=util_embed(
                "Komutlar Tazelendi",
                f"**{len(synced)}** slash komutu Discord ile senkronize edildi.",
                discord.Color.green(),
            ),
            ephemeral=True,
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=util_embed("Yetki Hatası", "Bu komutu kullanmak için **Yönetici** yetkisine ihtiyacınız var.", discord.Color.red()),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(str(error), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
