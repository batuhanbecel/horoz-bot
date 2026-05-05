import discord
from discord import app_commands
from discord.ext import commands
from datetime import timezone, datetime
from ._shared import _emb


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._start_time = datetime.now(timezone.utc)

    # /ping
    @app_commands.command(name="ping", description="Botun gecikme süresini gösterir.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        color   = discord.Color.green() if latency < 100 else discord.Color.orange() if latency < 200 else discord.Color.red()
        bar_len = min(int(latency / 20), 10)
        bar     = "█" * bar_len + "░" * (10 - bar_len)
        await interaction.response.send_message(embed=_emb("🏓 Pong!", f"`{bar}` **{latency} ms**", color))

    # /avatar
    @app_commands.command(name="avatar", description="Bir kullanıcının avatarını gösterir.")
    @app_commands.describe(üye="Avatarı gösterilecek üye (boş = kendiniz)")
    async def avatar(self, interaction: discord.Interaction, üye: discord.Member = None):
        target = üye or interaction.user
        embed  = discord.Embed(title=f"🖼️ {target.display_name}", color=discord.Color.blurple())
        embed.set_image(url=target.display_avatar.with_size(1024).url)
        embed.description = (
            f"[PNG]({target.display_avatar.with_format('png').url}) · "
            f"[JPG]({target.display_avatar.with_format('jpg').url}) · "
            f"[WEBP]({target.display_avatar.with_format('webp').url})"
        )
        embed.set_footer(text="Horoz Bot")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    # /bot
    @app_commands.command(name="bot", description="Bot hakkında bilgi verir.")
    async def horoz_info(self, interaction: discord.Interaction):
        delta  = datetime.now(timezone.utc) - self._start_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s   = divmod(rem, 60)

        embed = discord.Embed(title="🐓 Horoz Bot", color=discord.Color.blurple())
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="🌐 Sunucu",     value=str(len(self.bot.guilds)),                                  inline=True)
        embed.add_field(name="👥 Üye",        value=str(sum(g.member_count for g in self.bot.guilds)),           inline=True)
        embed.add_field(name="📡 Gecikme",    value=f"{round(self.bot.latency * 1000)} ms",                     inline=True)
        embed.add_field(name="⏱️ Çalışma",    value=f"{h}s {m}d {s}sn",                                        inline=True)
        embed.add_field(name="🐍 discord.py", value=discord.__version__,                                        inline=True)
        embed.add_field(name="📦 GitHub",     value="[batuhanbecel/horoz-bot](https://github.com/batuhanbecel/horoz-bot)", inline=True)
        embed.set_footer(text="Horoz Bot")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    # /profil
    @app_commands.command(name="profil", description="Bir kullanıcı hakkında bilgi verir.")
    @app_commands.describe(üye="Bilgi alınacak üye (boş = kendiniz)")
    async def profil(self, interaction: discord.Interaction, üye: discord.Member = None):
        target = üye or interaction.user
        color  = target.color if target.color != discord.Color.default() else discord.Color.blurple()

        embed = discord.Embed(title=f"👤 {target.display_name}", color=color)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Kullanıcı", value=str(target),                           inline=True)
        embed.add_field(name="ID",        value=f"`{target.id}`",                       inline=True)
        embed.add_field(name="Bot?",      value="✅ Evet" if target.bot else "❌ Hayır", inline=True)

        created = target.created_at.replace(tzinfo=timezone.utc)
        embed.add_field(name="📅 Hesap Açıldı", value=f"<t:{int(created.timestamp())}:F>", inline=True)

        if isinstance(target, discord.Member):
            joined = target.joined_at.replace(tzinfo=timezone.utc)
            embed.add_field(name="📥 Sunucuya Katılım", value=f"<t:{int(joined.timestamp())}:F>", inline=True)
            embed.add_field(name="​", value="​", inline=True)
            roles = [r.mention for r in reversed(target.roles) if r.name != "@everyone"]
            embed.add_field(
                name=f"🏷️ Roller ({len(roles)})",
                value=", ".join(roles[:10]) or "Yok",
                inline=False,
            )

        embed.set_footer(text="Horoz Bot")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    # /sunucu
    @app_commands.command(name="sunucu", description="Sunucu hakkında bilgi verir.")
    async def sunucu(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"🏠 {guild.name}", color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.with_size(1024).url)

        created = guild.created_at.replace(tzinfo=timezone.utc)
        embed.add_field(name="👑 Sahip",       value=guild.owner.mention if guild.owner else "Bilinmiyor",        inline=True)
        embed.add_field(name="🆔 ID",          value=f"`{guild.id}`",                                             inline=True)
        embed.add_field(name="📅 Oluşturuldu", value=f"<t:{int(created.timestamp())}:R>",                         inline=True)
        embed.add_field(name="👥 Üye",         value=str(guild.member_count),                                     inline=True)
        embed.add_field(name="💬 Kanal",       value=f"{len(guild.text_channels)} metin · {len(guild.voice_channels)} ses", inline=True)
        embed.add_field(name="🏷️ Rol",         value=str(len(guild.roles)),                                       inline=True)
        embed.add_field(name="✨ Boost",        value=f"Seviye **{guild.premium_tier}** — {guild.premium_subscription_count} boost", inline=True)
        embed.add_field(name="🔒 Doğrulama",   value=str(guild.verification_level).title(),                       inline=True)
        embed.add_field(name="😀 Emoji",        value=f"{len(guild.emojis)}/{guild.emoji_limit}",                  inline=True)
        embed.set_footer(text="Horoz Bot")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(embed=_emb("❌ Hata", str(error), discord.Color.red()), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))
