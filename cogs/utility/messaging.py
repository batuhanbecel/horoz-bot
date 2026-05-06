import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from ._shared import RENK_MAP, MesajModal, EmbedModal, DuyuruModal
from .._v2 import (
    COLORS, c_card, c_action_card, c_text, c_section, c_thumbnail, c_separator, c_container,
    respond, channel_send, error_response,
)


class Messaging(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Task referanslarını GC'den koru
        self._reminders: set[asyncio.Task] = set()

    # /yaz
    @app_commands.command(name="yaz", description="Seçilen kanala botun ağzından mesaj gönderir.")
    @app_commands.describe(kanal="Mesajın gönderileceği kanal")
    @app_commands.guild_only()
    async def yaz(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_messages:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Mesajları Yönet** yetkisi gereklidir.", color=COLORS.DANGER),
                ephemeral=True,
            )
        await interaction.response.send_modal(MesajModal(kanal))

    # /embed
    @app_commands.command(name="embed", description="Seçilen kanala embed mesaj gönderir.")
    @app_commands.describe(kanal="Mesajın gönderileceği kanal", renk="Embed kenar rengi")
    @app_commands.choices(renk=[
        app_commands.Choice(name="🔵 Mavi",    value="mavi"),
        app_commands.Choice(name="🟢 Yeşil",   value="yesil"),
        app_commands.Choice(name="🔴 Kırmızı", value="kirmizi"),
        app_commands.Choice(name="🟡 Altın",   value="altin"),
        app_commands.Choice(name="🟣 Mor",     value="mor"),
        app_commands.Choice(name="🟠 Turuncu", value="turuncu"),
        app_commands.Choice(name="🩷 Pembe",   value="pembe"),
    ])
    @app_commands.guild_only()
    async def embed_gonder(self, interaction: discord.Interaction, kanal: discord.TextChannel, renk: str = "mavi"):
        if not interaction.user.guild_permissions.manage_messages:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Mesajları Yönet** yetkisi gereklidir.", color=COLORS.DANGER),
                ephemeral=True,
            )
        await interaction.response.send_modal(EmbedModal(kanal, RENK_MAP.get(renk, 0x3498DB)))

    # /duyuru
    @app_commands.command(name="duyuru", description="Seçilen kanala duyuru gönderir.")
    @app_commands.describe(kanal="Duyurunun gönderileceği kanal", ping="Ping türü")
    @app_commands.choices(ping=[
        app_commands.Choice(name="@everyone", value="@everyone"),
        app_commands.Choice(name="@here",     value="@here"),
        app_commands.Choice(name="Ping Yok",  value=""),
    ])
    @app_commands.guild_only()
    async def duyuru(self, interaction: discord.Interaction, kanal: discord.TextChannel, ping: str = ""):
        if not interaction.user.guild_permissions.manage_messages:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="**Mesajları Yönet** yetkisi gereklidir.", color=COLORS.DANGER),
                ephemeral=True,
            )
        await interaction.response.send_modal(DuyuruModal(kanal, ping))

    # /hatırlat
    @app_commands.command(name="hatırlat", description="Belirlenen dakika sonra DM ile hatırlatma gönderir.")
    @app_commands.describe(dakika="Kaç dakika sonra (1-1440)", mesaj="Hatırlatma mesajı")
    async def hatirlat(
        self,
        interaction: discord.Interaction,
        dakika: app_commands.Range[int, 1, 1440],
        mesaj: str = "Hatırlatma!",
    ):
        from datetime import timedelta
        when = discord.utils.utcnow() + timedelta(minutes=dakika)

        await respond(interaction, c_action_card(
            "⏰ Hatırlatma Kuruldu",
            fields=[
                ("⏱️ Süre", f"`{dakika}` dakika sonra"),
                ("🕐 Zaman", f"<t:{int(when.timestamp())}:F>\n┗ <t:{int(when.timestamp())}:R>"),
                ("📝 Mesaj", f"> {mesaj}"),
            ],
            footer="DM kapalıysa hatırlatma ulaşmayacaktır.",
            color=COLORS.GAME,
        ), ephemeral=True)

        guild_name = interaction.guild.name if interaction.guild else "DM"

        async def _remind():
            try:
                await asyncio.sleep(dakika * 60)
                dm = await interaction.user.create_dm()
                await channel_send(dm, c_container(
                    c_text("## ⏰ Hatırlatma!"),
                    c_separator(),
                    c_text(f"📝 {mesaj}"),
                    c_separator(),
                    c_text(f"-# {dakika} dk önce **{guild_name}** sunucusunda ayarlandı."),
                    color=COLORS.GAME,
                ))
            except (discord.Forbidden, discord.HTTPException):
                pass

        task = asyncio.create_task(_remind())
        self._reminders.add(task)
        task.add_done_callback(self._reminders.discard)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await error_response(interaction, str(error))


async def setup(bot: commands.Bot):
    await bot.add_cog(Messaging(bot))
