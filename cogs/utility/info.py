import discord
from discord import app_commands
from discord.ext import commands
from datetime import timezone, datetime
from .._v2 import (
    COLORS, c_card, c_info_card, c_text, c_thumbnail, c_separator, c_section, c_container, c_media,
    c_progress, respond, edit_original, error_response,
)


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._start_time = datetime.now(timezone.utc)

    # /ping ─ multi-section latency card
    @app_commands.command(name="ping", description="Botun gecikme süresini gösterir.")
    async def ping(self, interaction: discord.Interaction):
        ws = round(self.bot.latency * 1000)
        thumb = str(self.bot.user.display_avatar.url)

        before = discord.utils.utcnow()
        await respond(interaction, c_card("## 🏓 Pong!", body="`▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱` Ölçülüyor...", thumbnail=thumb, color=COLORS.PRIMARY))
        rt = round((discord.utils.utcnow() - before).total_seconds() * 1000)

        ws_color = COLORS.SUCCESS if ws < 100 else COLORS.WARNING if ws < 200 else COLORS.DANGER
        ws_status = "🟢 Mükemmel" if ws < 100 else "🟡 Normal" if ws < 200 else "🔴 Yüksek"
        rt_status = "🟢 Mükemmel" if rt < 200 else "🟡 Normal" if rt < 500 else "🔴 Yüksek"

        bar = c_progress(min(ws, 360), 360, length=18)

        await edit_original(interaction, c_container(
            c_section(c_text("## 🏓 Pong!"), accessory=c_thumbnail(thumb)),
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

    # /bot ─ rich info card with grouped stats
    @app_commands.command(name="bot", description="Bot hakkında bilgi verir.")
    async def horoz_info(self, interaction: discord.Interaction):
        delta = datetime.now(timezone.utc) - self._start_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        d, h = divmod(h, 24)
        uptime = f"{d}g {h}sa {m}dk {s}sn" if d else f"{h}sa {m}dk {s}sn"

        members = sum(g.member_count for g in self.bot.guilds)

        await respond(interaction, c_info_card(
            "🐓 Horoz Bot",
            thumbnail=str(self.bot.user.display_avatar.url),
            groups=[
                [
                    ("🌐 Sunucu", f"`{len(self.bot.guilds)}`"),
                    ("👥 Toplam Üye", f"`{members:,}`"),
                    ("📡 Gecikme", f"`{round(self.bot.latency * 1000)} ms`"),
                ],
                [
                    ("⏱️ Çalışma Süresi", uptime),
                    ("🐍 discord.py", f"`{discord.__version__}`"),
                    ("📦 Repo", "[batuhanbecel/horoz-bot](https://github.com/batuhanbecel/horoz-bot)"),
                ],
            ],
            footer="Components V2 · 8top tarzı arayüz",
            color=COLORS.PRIMARY,
        ))

    # /profil ─ multi-section profile card
    @app_commands.command(name="profil", description="Bir kullanıcı hakkında bilgi verir.")
    @app_commands.describe(üye="Bilgi alınacak üye (boş = kendiniz)")
    async def profil(self, interaction: discord.Interaction, üye: discord.Member = None):
        target = üye or interaction.user
        color = target.color.value if isinstance(target, discord.Member) and target.color != discord.Color.default() else COLORS.PRIMARY

        created = target.created_at.replace(tzinfo=timezone.utc)
        identity = [
            ("👤 Kullanıcı Adı", f"`{target}`"),
            ("🆔 ID", f"`{target.id}`"),
            ("🤖 Bot", "Evet ✅" if target.bot else "Hayır ❌"),
            ("📅 Hesap Oluşturuldu", f"<t:{int(created.timestamp())}:F>\n┗ <t:{int(created.timestamp())}:R>"),
        ]
        groups: list = [identity]

        if isinstance(target, discord.Member):
            member_group: list[tuple[str, str]] = []
            if target.joined_at:
                joined = target.joined_at.replace(tzinfo=timezone.utc)
                member_group.append(("📥 Sunucuya Katılım", f"<t:{int(joined.timestamp())}:F>\n┗ <t:{int(joined.timestamp())}:R>"))
            if target.premium_since:
                boost = target.premium_since.replace(tzinfo=timezone.utc)
                member_group.append(("✨ Boost Veriyor", f"<t:{int(boost.timestamp())}:R>"))
            roles = [r.mention for r in reversed(target.roles) if r.name != "@everyone"]
            member_group.append(("🏷️ En Yüksek Rol", target.top_role.mention if target.top_role.name != "@everyone" else "_Yok_"))
            member_group.append(("📊 Rol Sayısı", f"`{len(roles)}`"))
            if member_group:
                groups.append(member_group)
            if roles:
                role_list = ", ".join(roles[:15]) + (f" `+{len(roles)-15}`" if len(roles) > 15 else "")
                groups.append(f"**🏷️ Roller**\n{role_list}")

        await respond(interaction, c_info_card(
            f"👤 {target.display_name}",
            thumbnail=str(target.display_avatar.url),
            groups=groups,
            footer=f"Profil görüntüleyici · {target}",
            color=color,
        ))

    # /sunucu ─ rich server info card with banner
    @app_commands.command(name="sunucu", description="Sunucu hakkında bilgi verir.")
    async def sunucu(self, interaction: discord.Interaction):
        guild = interaction.guild
        created = guild.created_at.replace(tzinfo=timezone.utc)

        humans = sum(1 for m in guild.members if not m.bot)
        bots = guild.member_count - humans
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)

        identity = [
            ("👑 Sahip", guild.owner.mention if guild.owner else "_Bilinmiyor_"),
            ("🆔 ID", f"`{guild.id}`"),
            ("📅 Kuruluş", f"<t:{int(created.timestamp())}:F>\n┗ <t:{int(created.timestamp())}:R>"),
            ("🔒 Doğrulama", f"`{str(guild.verification_level).title()}`"),
        ]
        members = [
            ("👥 Toplam Üye", f"`{guild.member_count:,}`"),
            ("🧑 İnsan", f"`{humans:,}`"),
            ("🤖 Bot", f"`{bots:,}`"),
            ("🟢 Aktif", f"`{online:,}`"),
        ]
        channels = [
            ("💬 Metin Kanalı", f"`{len(guild.text_channels)}`"),
            ("🔊 Ses Kanalı", f"`{len(guild.voice_channels)}`"),
            ("📁 Kategori", f"`{len(guild.categories)}`"),
            ("🧵 Thread", f"`{len(guild.threads)}`"),
        ]
        extras = [
            ("🏷️ Rol", f"`{len(guild.roles)}`"),
            ("😀 Emoji", f"`{len(guild.emojis)}/{guild.emoji_limit}`"),
            ("🏷️ Sticker", f"`{len(guild.stickers)}/{guild.sticker_limit}`"),
            ("✨ Boost", f"Seviye `{guild.premium_tier}` · `{guild.premium_subscription_count}` boost"),
        ]

        await respond(interaction, c_info_card(
            f"🏠 {guild.name}",
            thumbnail=str(guild.icon.url) if guild.icon else None,
            groups=[identity, members, channels, extras],
            media=str(guild.banner.with_size(1024).url) if guild.banner else None,
            footer=f"Sunucu bilgisi · {guild.name}",
            color=COLORS.INFO,
        ))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await error_response(interaction, str(error))


async def setup(bot: commands.Bot):
    await bot.add_cog(Info(bot))
