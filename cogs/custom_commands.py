import discord
from discord import app_commands
from discord.ext import commands
from database import db


def _emb(title: str, desc: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text="Horoz Bot • Özel Komutlar")
    e.timestamp = discord.utils.utcnow()
    return e


class CustomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /komut-yarat
    @app_commands.command(name="komut-yarat", description="Sunucuya özel bir komut oluşturur.")
    @app_commands.describe(
        isim="Komut ismi (boşluksuz, küçük harf, max 32 karakter)",
        yanıt="Komut çalıştırıldığında gönderilecek mesaj",
    )
    async def komut_yarat(self, interaction: discord.Interaction, isim: str, yanıt: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "Bu komut için **Sunucuyu Yönet** yetkisi gereklidir.", discord.Color.red()),
                ephemeral=True,
            )

        isim = isim.lower().strip().replace(" ", "-")
        if not (2 <= len(isim) <= 32):
            return await interaction.response.send_message(
                embed=_emb("❌ Geçersiz İsim", "Komut ismi **2–32** karakter arasında olmalıdır.", discord.Color.red()),
                ephemeral=True,
            )

        if await db.get_custom_command(interaction.guild_id, isim):
            return await interaction.response.send_message(
                embed=_emb("❌ Zaten Mevcut", f"`{isim}` adında bir komut zaten var.\n`/komut-sil` ile önce silebilirsiniz.", discord.Color.red()),
                ephemeral=True,
            )

        await db.create_custom_command(interaction.guild_id, isim, yanıt, interaction.user.id)
        embed = _emb("✅ Komut Oluşturuldu", color=discord.Color.green())
        embed.add_field(name="İsim",     value=f"`{isim}`",                inline=True)
        embed.add_field(name="Kullanım", value=f"`/komut isim:{isim}`",    inline=True)
        preview = yanıt[:100] + ("..." if len(yanıt) > 100 else "")
        embed.add_field(name="Yanıt Önizleme", value=preview, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /komut-liste
    @app_commands.command(name="komut-liste", description="Sunucudaki özel komutları listeler.")
    async def komut_liste(self, interaction: discord.Interaction):
        rows = await db.list_custom_commands(interaction.guild_id)
        if not rows:
            return await interaction.response.send_message(
                embed=_emb("📋 Özel Komutlar", "Bu sunucuda henüz özel komut oluşturulmamış.\n`/komut-yarat` ile ekleyebilirsiniz.", discord.Color.orange()),
                ephemeral=True,
            )

        embed = discord.Embed(
            title=f"📋 Özel Komutlar — {len(rows)} adet",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Horoz Bot • Özel Komutlar")
        embed.timestamp = discord.utils.utcnow()

        for row in rows[:25]:
            preview = row["response"][:80] + "..." if len(row["response"]) > 80 else row["response"]
            embed.add_field(name=f"🔸 /{row['name']}", value=preview, inline=False)

        if len(rows) > 25:
            embed.set_footer(text=f"Horoz Bot • İlk 25 komut gösteriliyor, toplam {len(rows)}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /komut-sil
    @app_commands.command(name="komut-sil", description="Bir özel komutu siler.")
    @app_commands.describe(isim="Silinecek komutun ismi")
    async def komut_sil(self, interaction: discord.Interaction, isim: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=_emb("❌ Yetersiz Yetki", "Bu komut için **Sunucuyu Yönet** yetkisi gereklidir.", discord.Color.red()),
                ephemeral=True,
            )
        isim = isim.lower().strip()
        if await db.delete_custom_command(interaction.guild_id, isim):
            await interaction.response.send_message(
                embed=_emb("🗑️ Komut Silindi", f"`{isim}` komutu başarıyla silindi.", discord.Color.green()),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=_emb("❌ Bulunamadı", f"`{isim}` adında bir komut bulunamadı.", discord.Color.red()),
                ephemeral=True,
            )

    # /komut
    @app_commands.command(name="komut", description="Bir özel komutu çalıştırır.")
    @app_commands.describe(isim="Çalıştırılacak komutun ismi")
    async def komut(self, interaction: discord.Interaction, isim: str):
        isim = isim.lower().strip()
        row  = await db.get_custom_command(interaction.guild_id, isim)
        if not row:
            return await interaction.response.send_message(
                embed=_emb("❌ Bulunamadı", f"`{isim}` adında bir komut yok.\n`/komut-liste` ile mevcut komutları görebilirsiniz.", discord.Color.red()),
                ephemeral=True,
            )
        await interaction.response.send_message(row["response"])

    @komut.autocomplete("isim")
    async def komut_autocomplete(self, interaction: discord.Interaction, current: str):
        names = await db.get_command_names(interaction.guild_id)
        return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]

    @komut_sil.autocomplete("isim")
    async def komut_sil_autocomplete(self, interaction: discord.Interaction, current: str):
        names = await db.get_command_names(interaction.guild_id)
        return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = str(error)
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(embed=_emb("❌ Hata", msg, discord.Color.red()), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CustomCommands(bot))
