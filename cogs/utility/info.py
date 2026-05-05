import discord
from discord import app_commands
from discord.ext import commands
from datetime import timezone, datetime
from ._shared import _emb
from .._v2 import (
    c_text, c_thumbnail, c_separator, c_section, c_container, c_media,
    respond, edit_original,
)


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._start_time = datetime.now(timezone.utc)

    # /ping
    @app_commands.command(name="ping", description="Botun gecikme süresini gösterir.")
    async def ping(self, interaction: discord.Interaction):
        ws = round(self.bot.latency * 1000)
        color = 0x57F287 if ws < 100 else 0xFEE75C if ws < 200 else 0xED4245

        before = discord.utils.utcnow()
        await respond(interaction, c_container(c_text("**🏓 Pong!**\n\nÖlçülüyor..."), color=color))
        rt = round((discord.utils.utcnow() - before).total_seconds() * 1000)

        bar_len = min(int(ws / 20), 10)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        await edit_original(interaction, c_container(
            c_text(
                f"**🏓 Pong!**\n\n"
                f"`{bar}`\n\n"
                f"📡 **WebSocket:** {ws} ms\n"
                f"🔄 **Roundtrip:** {rt} ms"
            ),
            color=color,
        ))

    # /avatar
    @app_commands.command(name="avatar", description="Bir kullanıcının avatarını gösterir.")
    @app_commands.describe(üye="Avatarı gösterilecek üye (boş = kendiniz)")
    async def avatar(self, interaction: discord.Interaction, üye: discord.Member = None):
        target = üye or interaction.user
        av_url = str(target.display_avatar.with_size(1024).url)
        links = (
            f"[PNG]({target.display_avatar.with_format('png').url}) · "
            f"[JPG]({target.display_avatar.with_format('jpg').url}) · "
            f"[WEBP]({target.display_avatar.with_format('webp').url})"
        )
        await respond(interaction, c_container(
            c_section(
                c_text(f"**🖼️ {target.display_name}**\n\n{links}"),
                accessory=c_thumbnail(av_url),
            ),
            c_separator(),
            c_media(av_url),
            color=0x5865F2,
        ))

    # /bot
    @app_commands.command(name="bot", description="Bot hakkında bilgi verir.")
    async def horoz_info(self, interaction: discord.Interaction):
        delta = datetime.now(timezone.utc) - self._start_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s = divmod(rem, 60)

        text = (
            "**🐓 Horoz Bot**\n\n"
            f"🌐 **Sunucu:** {len(self.bot.guilds)}\n"
            f"👥 **Üye:** {sum(g.member_count for g in self.bot.guilds)}\n"
            f"📡 **Gecikme:** {round(self.bot.latency * 1000)} ms\n"
            f"⏱️ **Çalışma:** {h}s {m}d {s}sn\n"
            f"🐍 **discord.py:** {discord.__version__}\n"
            f"📦 **GitHub:** [batuhanbecel/horoz-bot](https://github.com/batuhanbecel/horoz-bot)"
        )
        await respond(interaction, c_container(
            c_section(
                c_text(text),
                accessory=c_thumbnail(str(self.bot.user.display_avatar.url)),
            ),
            color=0x5865F2,
        ))

    # /profil
    @app_commands.command(name="profil", description="Bir kullanıcı hakkında bilgi verir.")
    @app_commands.describe(üye="Bilgi alınacak üye (boş = kendiniz)")
    async def profil(self, interaction: discord.Interaction, üye: discord.Member = None):
        target = üye or interaction.user
        color = target.color.value if target.color != discord.Color.default() else 0x5865F2

        created = target.created_at.replace(tzinfo=timezone.utc)
        lines = [
            f"**👤 {target.display_name}**",
            "",
            f"👤 **Kullanıcı:** {target}",
            f"🆔 **ID:** `{target.id}`",
            f"🤖 **Bot:** {'✅ Evet' if target.bot else '❌ Hayır'}",
            f"📅 **Hesap Açıldı:** <t:{int(created.timestamp())}:F>",
        ]

        if isinstance(target, discord.Member) and target.joined_at:
            joined = target.joined_at.replace(tzinfo=timezone.utc)
            lines.append(f"📥 **Sunucuya Katılım:** <t:{int(joined.timestamp())}:F>")
            roles = [r.mention for r in reversed(target.roles) if r.name != "@everyone"]
            lines.append(f"🏷️ **Roller ({len(roles)}):** {', '.join(roles[:10]) or 'Yok'}")

        await respond(interaction, c_container(
            c_section(
                c_text("\n".join(lines)),
                accessory=c_thumbnail(str(target.display_avatar.url)),
            ),
            color=color,
        ))

    # /sunucu
    @app_commands.command(name="sunucu", description="Sunucu hakkında bilgi verir.")
    async def sunucu(self, interaction: discord.Interaction):
        guild = interaction.guild
        created = guild.created_at.replace(tzinfo=timezone.utc)

        lines = [
            f"**🏠 {guild.name}**",
            "",
            f"👑 **Sahip:** {guild.owner.mention if guild.owner else 'Bilinmiyor'}",
            f"🆔 **ID:** `{guild.id}`",
            f"📅 **Oluşturuldu:** <t:{int(created.timestamp())}:R>",
            f"👥 **Üye:** {guild.member_count}",
            f"💬 **Kanal:** {len(guild.text_channels)} metin · {len(guild.voice_channels)} ses",
            f"🏷️ **Rol:** {len(guild.roles)}",
            f"✨ **Boost:** Seviye **{guild.premium_tier}** — {guild.premium_subscription_count} boost",
            f"🔒 **Doğrulama:** {str(guild.verification_level).title()}",
            f"😀 **Emoji:** {len(guild.emojis)}/{guild.emoji_limit}",
        ]

        icon_url = str(guild.icon.url) if guild.icon else None
        main = (
            c_section(c_text("\n".join(lines)), accessory=c_thumbnail(icon_url))
            if icon_url
            else c_text("\n".join(lines))
        )

        card_items = [main]
        if guild.banner:
            card_items.append(c_separator())
            card_items.append(c_media(str(guild.banner.with_size(1024).url)))

        await respond(interaction, c_container(*card_items, color=0x5865F2))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(embed=_emb("❌ Hata", str(error), discord.Color.red()), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))
