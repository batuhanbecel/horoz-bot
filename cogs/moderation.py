import discord
from discord import app_commands
from discord.ext import commands
from database import db
import re
from datetime import timedelta


def parse_duration(text: str) -> timedelta | None:
    """'10m', '2h', '1d' gibi süre stringlerini timedelta'ya çevirir."""
    match = re.fullmatch(r"(\d+)([smhd])", text.strip().lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    return {"s": timedelta(seconds=value), "m": timedelta(minutes=value),
            "h": timedelta(hours=value), "d": timedelta(days=value)}[unit]


def mod_embed(title: str, description: str, color: discord.Color = discord.Color.red()) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    return embed


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    mod = app_commands.Group(name="moderatör", description="Moderasyon komutları")

    # /moderatör temizle
    @mod.command(name="temizle", description="Belirtilen sayıda mesajı siler.")
    @app_commands.describe(miktar="Silinecek mesaj sayısı (1-100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def temizle(self, interaction: discord.Interaction, miktar: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=miktar)
        await interaction.followup.send(
            embed=mod_embed("Temizlendi", f"{len(deleted)} mesaj silindi.", discord.Color.green()),
            ephemeral=True,
        )

    # /moderatör at
    @mod.command(name="at", description="Bir üyeyi sunucudan atar.")
    @app_commands.describe(üye="Atılacak üye", sebep="Atılma sebebi")
    @app_commands.checks.has_permissions(kick_members=True)
    async def at(self, interaction: discord.Interaction, üye: discord.Member, sebep: str = "Belirtilmedi"):
        if üye.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=mod_embed("Hata", "Bu üyeye işlem yapamazsınız."), ephemeral=True
            )
            return
        await üye.kick(reason=f"{interaction.user}: {sebep}")
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "kick")
        await interaction.response.send_message(
            embed=mod_embed("Atıldı", f"{üye.mention} sunucudan atıldı.\n**Sebep:** {sebep}", discord.Color.orange())
        )

    # /moderatör yasakla
    @mod.command(name="yasakla", description="Bir üyeyi kalıcı olarak yasaklar.")
    @app_commands.describe(üye="Yasaklanacak üye", sebep="Yasaklama sebebi", mesaj_sil="Kaç günlük mesaj silinsin (0-7)")
    @app_commands.checks.has_permissions(ban_members=True)
    async def yasakla(
        self,
        interaction: discord.Interaction,
        üye: discord.Member,
        sebep: str = "Belirtilmedi",
        mesaj_sil: app_commands.Range[int, 0, 7] = 0,
    ):
        if üye.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=mod_embed("Hata", "Bu üyeye işlem yapamazsınız."), ephemeral=True
            )
            return
        await üye.ban(reason=f"{interaction.user}: {sebep}", delete_message_days=mesaj_sil)
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "ban")
        await interaction.response.send_message(
            embed=mod_embed("Yasaklandı", f"{üye.mention} yasaklandı.\n**Sebep:** {sebep}")
        )

    # /moderatör sustur
    @mod.command(name="sustur", description="Bir üyeyi timeout ile susturur.")
    @app_commands.describe(üye="Susturulacak üye", süre="Süre (örn: 10m, 2h, 1d)", sebep="Susturma sebebi")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def sustur(
        self,
        interaction: discord.Interaction,
        üye: discord.Member,
        süre: str,
        sebep: str = "Belirtilmedi",
    ):
        delta = parse_duration(süre)
        if not delta:
            await interaction.response.send_message(
                embed=mod_embed("Hata", "Geçersiz süre. Örnek: `10m`, `2h`, `1d`"), ephemeral=True
            )
            return
        if delta > timedelta(days=28):
            await interaction.response.send_message(
                embed=mod_embed("Hata", "Maksimum susturma süresi 28 gündür."), ephemeral=True
            )
            return
        await üye.timeout(delta, reason=f"{interaction.user}: {sebep}")
        await db.add_infraction(interaction.guild_id, üye.id, interaction.user.id, sebep, "mute")
        await interaction.response.send_message(
            embed=mod_embed(
                "Susturuldu",
                f"{üye.mention} **{süre}** süreyle susturuldu.\n**Sebep:** {sebep}",
                discord.Color.yellow(),
            )
        )

    # /moderatör sustu-kaldır
    @mod.command(name="sustu-kaldır", description="Bir üyenin susturmasını kaldırır.")
    @app_commands.describe(üye="Susturması kaldırılacak üye")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def sustu_kaldir(self, interaction: discord.Interaction, üye: discord.Member):
        if not üye.is_timed_out():
            await interaction.response.send_message(
                embed=mod_embed("Hata", "Bu üye zaten susturulmuş değil."), ephemeral=True
            )
            return
        await üye.timeout(None)
        await interaction.response.send_message(
            embed=mod_embed("Susturma Kaldırıldı", f"{üye.mention} artık konuşabilir.", discord.Color.green())
        )

    # /moderatör ihlaller
    @mod.command(name="ihlaller", description="Bir üyenin ihlal geçmişini gösterir.")
    @app_commands.describe(üye="İhlalleri görüntülenecek üye")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def ihlaller(self, interaction: discord.Interaction, üye: discord.Member):
        rows = await db.get_infractions(interaction.guild_id, üye.id)
        if not rows:
            await interaction.response.send_message(
                embed=mod_embed("İhlaller", f"{üye.mention} için kayıtlı ihlal yok.", discord.Color.green()),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"{üye.display_name} — İhlaller ({len(rows)})",
            color=discord.Color.orange(),
        )
        for i, row in enumerate(rows[:10], 1):
            mod = interaction.guild.get_member(row["mod_id"])
            mod_name = mod.display_name if mod else f"ID:{row['mod_id']}"
            embed.add_field(
                name=f"#{i} — {row['type'].upper()} ({row['created_at'][:10]})",
                value=f"**Mod:** {mod_name}\n**Sebep:** {row['reason'] or 'Yok'}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /moderatör ihlal-temizle
    @mod.command(name="ihlal-temizle", description="Bir üyenin tüm ihlallerini temizler.")
    @app_commands.describe(üye="İhlalleri temizlenecek üye")
    @app_commands.checks.has_permissions(administrator=True)
    async def ihlal_temizle(self, interaction: discord.Interaction, üye: discord.Member):
        await db.clear_infractions(interaction.guild_id, üye.id)
        await interaction.response.send_message(
            embed=mod_embed("Temizlendi", f"{üye.mention} tüm ihlalleri silindi.", discord.Color.green()),
            ephemeral=True,
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=mod_embed("Yetki Hatası", "Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz."),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=mod_embed("Hata", str(error)), ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
