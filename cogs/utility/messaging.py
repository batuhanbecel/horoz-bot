import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from ._shared import _emb, RENK_MAP, MesajModal, EmbedModal, DuyuruModal
from .._v2 import c_text, c_container, respond


class Messaging(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /yaz
    @app_commands.command(name="yaz", description="Seçilen kanala botun ağzından mesaj gönderir.")
    @app_commands.describe(kanal="Mesajın gönderileceği kanal")
    async def yaz(self, interaction: discord.Interaction, kanal: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Mesajları Yönet** yetkisi gereklidir.", discord.Color.red()),
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
    async def embed_gonder(self, interaction: discord.Interaction, kanal: discord.TextChannel, renk: str = "mavi"):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Mesajları Yönet** yetkisi gereklidir.", discord.Color.red()),
                ephemeral=True,
            )
        await interaction.response.send_modal(EmbedModal(kanal, RENK_MAP.get(renk, discord.Color.blue())))

    # /duyuru
    @app_commands.command(name="duyuru", description="Seçilen kanala duyuru gönderir.")
    @app_commands.describe(kanal="Duyurunun gönderileceği kanal", ping="Ping türü")
    @app_commands.choices(ping=[
        app_commands.Choice(name="@everyone", value="@everyone"),
        app_commands.Choice(name="@here",     value="@here"),
        app_commands.Choice(name="Ping Yok",  value=""),
    ])
    async def duyuru(self, interaction: discord.Interaction, kanal: discord.TextChannel, ping: str = ""):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "**Mesajları Yönet** yetkisi gereklidir.", discord.Color.red()),
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
        await respond(interaction,
            c_container(
                c_text(
                    f"**⏰ Hatırlatma Kuruldu**\n\n"
                    f"**{dakika} dakika** sonra DM olarak hatırlatılacaksın.\n> {mesaj}"
                ),
                color=0x57F287,
            ),
            ephemeral=True,
        )

        async def _remind():
            await asyncio.sleep(dakika * 60)
            try:
                await interaction.user.send(embed=_emb(
                    "⏰ Hatırlatma!",
                    f"{mesaj}\n\n*{dakika} dk önce **{interaction.guild.name}** sunucusunda ayarlandı.*",
                    discord.Color.gold(),
                ))
            except discord.Forbidden:
                pass

        asyncio.create_task(_remind())

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(embed=_emb("❌ Hata", str(error), discord.Color.red()), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Messaging(bot))
