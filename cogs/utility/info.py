import discord
from discord import app_commands
from discord.ext import commands
from datetime import timezone, datetime
from .._v2 import (
    c_card, c_text, c_thumbnail, c_separator, c_section, c_container, c_media,
    respond, edit_original, error_response,
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
        thumb = str(self.bot.user.display_avatar.url)

        before = discord.utils.utcnow()
        await respond(interaction, c_card("## 🏓 Pong!", body="Ölçülüyor...", thumbnail=thumb, color=color))
        rt = round((discord.utils.utcnow() - before).total_seconds() * 1000)

        bar_len = min(int(ws / 20), 10)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        await edit_original(interaction, c_card(
            "## 🏓 Pong!",
            body=f"`{bar}`\n\n📡 **WebSocket:** {ws} ms\n🔄 **Roundtrip:** {rt} ms",
            thumbnail=thumb,
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
                c_text(f"## 🖼️ {target.display_name}\n{links}"),
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
        body = (
            f"🌐 **Sunucu:** {len(self.bot.guilds)}\n"
            f"👥 **Üye:** {sum(g.member_count for g in self.bot.guilds)}\n"
            f"📡 **Gecikme:** {round(self.bot.latency * 1000)} ms\n"
            f"⏱️ **Çalışma:** {h}s {m}d {s}sn\n"
            f"🐍 **discord.py:** {discord.__version__}\n"
            f"📦 **GitHub:** [batuhanbecel/horoz-bot](https://github.com/batuhanbecel/horoz-bot)"
        )
        await respond(interaction, c_card(
            "## 🐓 Horoz Bot",
            body=body,
            thumbnail=str(self.bot.user.display_avatar.url),
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

        await respond(interaction, c_card(
            f"## 👤 {target.display_name}",
            body="\n".join(lines),
            thumbnail=str(target.display_avatar.url),
            color=color,
        ))

    # /sunucu
    @app_commands.command(name="sunucu", description="Sunucu hakkında bilgi verir.")
    async def sunucu(self, interaction: discord.Interaction):
        guild = interaction.guild
        created = guild.created_at.replace(tzinfo=timezone.utc)
        body = (
            f"👑 **Sahip:** {guild.owner.mention if guild.owner else 'Bilinmiyor'}\n"
            f"🆔 **ID:** `{guild.id}`\n"
            f"📅 **Oluşturuldu:** <t:{int(created.timestamp())}:R>\n"
            f"👥 **Üye:** {guild.member_count}\n"
            f"💬 **Kanal:** {len(guild.text_channels)} metin · {len(guild.voice_channels)} ses\n"
            f"🏷️ **Rol:** {len(guild.roles)}\n"
            f"✨ **Boost:** Seviye **{guild.premium_tier}** — {guild.premium_subscription_count} boost\n"
            f"🔒 **Doğrulama:** {str(guild.verification_level).title()}\n"
            f"😀 **Emoji:** {len(guild.emojis)}/{guild.emoji_limit}"
        )
        icon_url = str(guild.icon.url) if guild.icon else None
        base = c_card(f"## 🏠 {guild.name}", body=body, thumbnail=icon_url, color=0x5865F2)

        if guild.banner:
            items = list(base["components"])
            items.append(c_separator())
            items.append(c_media(str(guild.banner.with_size(1024).url)))
            base = dict(base) | {"components": items}

        await respond(interaction, base)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await error_response(interaction, str(error))


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))
