import discord
from discord import app_commands
from discord.ext import commands
from database import db


def cc_embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.timestamp = discord.utils.utcnow()
    return e


class CustomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /komutyarat
    @app_commands.command(name="komutyarat", description="Sunucuya özel bir komut oluşturur.")
    @app_commands.describe(
        isim="Komut ismi (boşluksuz, küçük harf)",
        yanıt="Komut çalıştırıldığında gönderilecek mesaj",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def komutyarat(self, interaction: discord.Interaction, isim: str, yanıt: str):
        isim = isim.lower().strip().replace(" ", "-")
        if len(isim) < 2 or len(isim) > 32:
            await interaction.response.send_message(
                embed=cc_embed("Hata", "Komut ismi 2-32 karakter arasında olmalıdır.", discord.Color.red()),
                ephemeral=True,
            )
            return

        existing = await db.get_custom_command(interaction.guild_id, isim)
        if existing:
            await interaction.response.send_message(
                embed=cc_embed("Hata", f"`{isim}` adında bir komut zaten mevcut.", discord.Color.red()),
                ephemeral=True,
            )
            return

        await db.create_custom_command(interaction.guild_id, isim, yanıt, interaction.user.id)
        await interaction.response.send_message(
            embed=cc_embed(
                "Komut Oluşturuldu",
                f"`{isim}` komutu başarıyla oluşturuldu.\nKullanmak için: `/komut isim:{isim}`",
                discord.Color.green(),
            ),
            ephemeral=True,
        )

    # /komutlistele
    @app_commands.command(name="komutlistele", description="Sunucudaki özel komutları listeler.")
    async def komutlistele(self, interaction: discord.Interaction):
        rows = await db.list_custom_commands(interaction.guild_id)
        if not rows:
            await interaction.response.send_message(
                embed=cc_embed("Özel Komutlar", "Bu sunucuda henüz özel komut yok.", discord.Color.orange()),
                ephemeral=True,
            )
            return

        embed = discord.Embed(title=f"Özel Komutlar ({len(rows)})", color=discord.Color.blurple())
        for row in rows[:25]:
            preview = row["response"][:60] + "..." if len(row["response"]) > 60 else row["response"]
            embed.add_field(name=f"/{row['name']}", value=preview, inline=False)

        if len(rows) > 25:
            embed.set_footer(text=f"ve {len(rows) - 25} komut daha... Tüm komutlar için sayfalar eklenmeli.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /komutsil
    @app_commands.command(name="komutsil", description="Bir özel komutu siler.")
    @app_commands.describe(isim="Silinecek komutun ismi")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def komutsil(self, interaction: discord.Interaction, isim: str):
        isim = isim.lower().strip()
        deleted = await db.delete_custom_command(interaction.guild_id, isim)
        if deleted:
            await interaction.response.send_message(
                embed=cc_embed("Komut Silindi", f"`{isim}` komutu silindi.", discord.Color.green()),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=cc_embed("Hata", f"`{isim}` adında bir komut bulunamadı.", discord.Color.red()),
                ephemeral=True,
            )

    # /komut
    @app_commands.command(name="komut", description="Bir özel komutu çalıştırır.")
    @app_commands.describe(isim="Çalıştırılacak komutun ismi")
    async def komut(self, interaction: discord.Interaction, isim: str):
        isim = isim.lower().strip()
        row = await db.get_custom_command(interaction.guild_id, isim)
        if not row:
            await interaction.response.send_message(
                embed=cc_embed("Hata", f"`{isim}` adında bir komut bulunamadı.\n`/komutlistele` ile mevcut komutları görebilirsin.", discord.Color.red()),
                ephemeral=True,
            )
            return
        await interaction.response.send_message(row["response"])

    @komut.autocomplete("isim")
    async def komut_autocomplete(self, interaction: discord.Interaction, current: str):
        names = await db.get_command_names(interaction.guild_id)
        return [
            app_commands.Choice(name=n, value=n)
            for n in names
            if current.lower() in n.lower()
        ][:25]

    @komutsil.autocomplete("isim")
    async def komutsil_autocomplete(self, interaction: discord.Interaction, current: str):
        names = await db.get_command_names(interaction.guild_id)
        return [
            app_commands.Choice(name=n, value=n)
            for n in names
            if current.lower() in n.lower()
        ][:25]

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=cc_embed("Yetki Hatası", "Bu komutu kullanmak için `Sunucuyu Yönet` yetkisine ihtiyacınız var.", discord.Color.red()),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(str(error), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CustomCommands(bot))
