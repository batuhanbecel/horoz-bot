import discord
from discord import app_commands
from discord.ext import commands
from datetime import timezone


def util_embed(title: str, color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    return discord.Embed(title=title, color=color)


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /yardım
    @app_commands.command(name="yardım", description="Tüm komutları listeler.")
    async def yardım(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🐓 Horoz Bot — Komut Listesi",
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="🛡️ /moderatör",
            value=(
                "`temizle` `at` `yasakla` `sustur`\n"
                "`sustu-kaldır` `ihlaller` `ihlal-temizle`"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎵 /müzik",
            value=(
                "`çal` `ara` `atla` `duraklat` `devam`\n"
                "`dur` `ses` `sıra` `sıra-temizle` `döngü`"
            ),
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
            value="`/yardım` `/kullanici-bilgi` `/sunucu-bilgi`",
            inline=False,
        )
        embed.set_footer(text="Horoz Bot | Tüm komutlar slash (/) ile kullanılır.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
        embed = discord.Embed(
            title=f"{guild.name} — Sunucu Bilgisi",
            color=discord.Color.blurple(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        created = guild.created_at.replace(tzinfo=timezone.utc)
        embed.add_field(name="Sahip", value=guild.owner.mention if guild.owner else "Bilinmiyor", inline=True)
        embed.add_field(name="ID", value=str(guild.id), inline=True)
        embed.add_field(name="Oluşturulma", value=f"<t:{int(created.timestamp())}:R>", inline=True)
        embed.add_field(name="Üye Sayısı", value=str(guild.member_count), inline=True)
        embed.add_field(name="Kanal Sayısı", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Rol Sayısı", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Boost Seviyesi", value=f"Seviye {guild.premium_tier} ({guild.premium_subscription_count} boost)", inline=True)
        embed.add_field(name="Doğrulama Seviyesi", value=str(guild.verification_level).title(), inline=True)

        text_ch = len(guild.text_channels)
        voice_ch = len(guild.voice_channels)
        embed.add_field(name="Kanallar", value=f"💬 {text_ch} metin | 🔊 {voice_ch} ses", inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
