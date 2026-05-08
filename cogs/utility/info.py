import discord
from discord import app_commands
from discord.ext import commands
from datetime import timezone, datetime
from .._v2 import (
    COLORS, c_card, c_info_card, c_rich_card, c_text, c_thumbnail, c_separator, c_section, c_container, c_media,
    c_progress, c_badge, c_status_indicator, respond, edit_original, error_response,
)


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._start_time = datetime.now(timezone.utc)

    # /ping ─ latency card (sade)
    @app_commands.command(name="ping", description="Botun gecikme süresini gösterir.")
    async def ping(self, interaction: discord.Interaction):
        ws = round(self.bot.latency * 1000)

        before = discord.utils.utcnow()
        await respond(interaction, c_card("## 🏓 Pong!", body="`▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱` Ölçülüyor...", color=COLORS.PRIMARY))
        rt = round((discord.utils.utcnow() - before).total_seconds() * 1000)

        ws_color = COLORS.SUCCESS if ws < 100 else COLORS.WARNING if ws < 200 else COLORS.DANGER
        ws_status = "🟢 Mükemmel" if ws < 100 else "🟡 Normal" if ws < 200 else "🔴 Yüksek"
        rt_status = "🟢 Mükemmel" if rt < 200 else "🟡 Normal" if rt < 500 else "🔴 Yüksek"

        bar = c_progress(min(ws, 360), 360, length=18)

        await edit_original(interaction, c_container(
            c_text("## 🏓 Pong!"),
            c_separator(),
            c_text(f"`{bar}`\n-# Gecikme grafiği · 0 — 360 ms"),
            c_separator(),
            c_text(
                f"📡 **WebSocket**\n"
                f"┗ `{ws} ms` · {ws_status}\n\n"
                f"🔄 **Roundtrip**\n"
                f"┗ `{rt} ms` · {rt_status}"
            ),
            color=ws_color,
        ))

    # /avatar ─ section header + full-size media
    @app_commands.command(name="avatar", description="Bir kullanıcının avatarını gösterir.")
    @app_commands.describe(üye="Avatarı gösterilecek üye (boş = kendiniz)")
    async def avatar(self, interaction: discord.Interaction, üye: discord.Member = None):
        target = üye or interaction.user
        av_url = str(target.display_avatar.with_size(1024).url)
        color = target.color.value if isinstance(target, discord.Member) and target.color != discord.Color.default() else COLORS.PRIMARY
        links = (
            f"[`PNG`]({target.display_avatar.with_format('png').url}) · "
            f"[`JPG`]({target.display_avatar.with_format('jpg').url}) · "
            f"[`WEBP`]({target.display_avatar.with_format('webp').url})"
        )
        await respond(interaction, c_container(
            c_section(
                c_text(f"## 🖼️ {target.display_name}\n-# Avatar görüntüleyici"),
                accessory=c_thumbnail(av_url),
            ),
            c_separator(),
            c_media(av_url),
            c_separator(),
            c_text(f"📥 **İndir:** {links}"),
            color=color,
        ))

    # /bot ─ rich info card with badge stats
    @app_commands.command(name="bot", description="Bot hakkında bilgi verir.")
    async def horoz_info(self, interaction: discord.Interaction):
        delta = datetime.now(timezone.utc) - self._start_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        d, h = divmod(h, 24)
        uptime = f"{d}g {h}sa {m}dk {s}sn" if d else f"{h}sa {m}dk {s}sn"

        members = sum(g.member_count or 0 for g in self.bot.guilds)
        ws = round(self.bot.latency * 1000)
        ping_color = "🟢" if ws < 100 else "🟡" if ws < 200 else "🔴"

        await respond(interaction, c_rich_card(
            "🐓 Horoz Bot",
            subtitle="Türkçe Discord Bot · v1.2+",
            thumbnail=str(self.bot.user.display_avatar.url),
            badges=[
                c_badge(f"discord.py {discord.__version__}", "🐍"),
                c_badge(f"{len(self.bot.guilds)} sunucu", "🌐"),
                c_badge(f"{members:,} üye", "👥"),
                c_badge(f"{ws}ms", ping_color),
            ],
            body="\n".join([
                c_status_indicator("ok", f"**Çalışma Süresi:** `{uptime}`"),
                c_status_indicator("info", f"**Gecikme:** `{ws} ms` {ping_color}"),
                c_status_indicator("info", f"**Repo:** [batuhanbecel/horoz-bot](https://github.com/batuhanbecel/horoz-bot)"),
                "",
                "**Komutlar:** /yardım ile tüm komutları görebilirsin.",
            ]),
            footer="Components V2 · V2 Modern",
            color=COLORS.PRIMARY,
        ))

    # /profil ─ rich profile card with badge stats
    @app_commands.command(name="profil", description="Bir kullanıcı hakkında bilgi verir.")
    @app_commands.describe(üye="Bilgi alınacak üye (boş = kendiniz)")
    async def profil(self, interaction: discord.Interaction, üye: discord.Member = None):
        target = üye or interaction.user
        color = target.color.value if isinstance(target, discord.Member) and target.color != discord.Color.default() else COLORS.PRIMARY

        created = target.created_at.replace(tzinfo=timezone.utc)
        badges: list[str] = [
            c_badge("Bot" if target.bot else "Kullanıcı", "🤖" if target.bot else "👤"),
            c_badge(f"ID: {target.id}", "🆔"),
        ]

        body_lines: list[str] = [
            c_status_indicator("info", f"**Hesap Oluşturuldu:** <t:{int(created.timestamp())}:F>"),
        ]

        roles: list[str] = []
        if isinstance(target, discord.Member):
            roles = [r.mention for r in reversed(target.roles) if r.name != "@everyone"]
            badges.append(c_badge(f"{len(roles)} rol", "🏷️"))
            if target.premium_since:
                boost = target.premium_since.replace(tzinfo=timezone.utc)
                badges.append(c_badge("Nitro Boost", "✨"))
            if target.joined_at:
                joined = target.joined_at.replace(tzinfo=timezone.utc)
                body_lines.append(c_status_indicator("ok", f"**Sunucuya Katılım:** <t:{int(joined.timestamp())}:F>"))
            body_lines.append("")
            body_lines.append(f"**En Yüksek Rol:** {target.top_role.mention if target.top_role.name != '@everyone' else '_Yok_'}")
            if roles:
                role_list = ", ".join(roles[:15]) + (f" `+{len(roles)-15}`" if len(roles) > 15 else "")
                body_lines.append(f"**Roller:** {role_list}")

        await respond(interaction, c_rich_card(
            f"👤 {target.display_name}",
            subtitle=f"`{target}`",
            thumbnail=str(target.display_avatar.url),
            badges=badges,
            body="\n".join(body_lines),
            footer=f"Profil görüntüleyici · {target}",
            color=color,
        ))

    # /sunucu ─ rich server info card with badges
    @app_commands.command(name="sunucu", description="Sunucu hakkında bilgi verir.")
    @app_commands.guild_only()
    async def sunucu(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            return await error_response(interaction, "Bu komut sadece sunucuda çalışır.")
        created = guild.created_at.replace(tzinfo=timezone.utc)

        cached = list(guild.members)
        toplam = guild.member_count or len(cached)
        online = sum(1 for m in cached if m.status != discord.Status.offline)

        verification = str(guild.verification_level).title()
        verif_emoji = "🔒" if guild.verification_level != discord.VerificationLevel.none else "🔓"

        badges = [
            c_badge(f"{toplam:,} üye", "👥"),
            c_badge(f"{online:,} aktif", "🟢"),
            c_badge(f"Seviye {guild.premium_tier} Boost", "✨"),
            c_badge(verification, verif_emoji),
        ]

        body_lines = [
            c_status_indicator("info", f"**Sahip:** {guild.owner.mention if guild.owner else '_Bilinmiyor_'}"),
            c_status_indicator("info", f"**Kuruluş:** <t:{int(created.timestamp())}:F>"),
            "",
            f"**Kanallar:** 💬 `{len(guild.text_channels)}` · 🔊 `{len(guild.voice_channels)}` · 📁 `{len(guild.categories)}` · 🧵 `{len(guild.threads)}`",
            f"**Roller & Emoji:** 🏷️ `{len(guild.roles)}` · 😀 `{len(guild.emojis)}/{guild.emoji_limit}` · 🏷️ `{len(guild.stickers)}/{guild.sticker_limit}`",
        ]

        await respond(interaction, c_rich_card(
            f"🏠 {guild.name}",
            subtitle=f"`{guild.id}`",
            thumbnail=str(guild.icon.url) if guild.icon else None,
            badges=badges,
            body="\n".join(body_lines),
            footer=f"Sunucu bilgisi · {guild.name}",
            color=COLORS.INFO,
        ))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await error_response(interaction, str(error))


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))
