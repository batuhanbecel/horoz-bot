import discord
from discord import app_commands
from discord.ext import commands
from database import db
from .._v2 import c_text, c_container, respond, followup as v2_followup


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
            return await respond(interaction,
                c_container(c_text("**❌ Yetersiz Yetki**\n\nBu komut için **Sunucuyu Yönet** yetkisi gereklidir."), color=0xED4245),
                ephemeral=True,
            )

        isim = isim.lower().strip().replace(" ", "-")
        if not (2 <= len(isim) <= 32):
            return await respond(interaction,
                c_container(c_text("**❌ Geçersiz İsim**\n\nKomut ismi **2–32** karakter arasında olmalıdır."), color=0xED4245),
                ephemeral=True,
            )

        if await db.get_custom_command(interaction.guild_id, isim):
            return await respond(interaction,
                c_container(c_text(f"**❌ Zaten Mevcut**\n\n`{isim}` adında bir komut zaten var.\n`/komut-sil` ile önce silebilirsiniz."), color=0xED4245),
                ephemeral=True,
            )

        await db.create_custom_command(interaction.guild_id, isim, yanıt, interaction.user.id)
        preview = yanıt[:100] + ("..." if len(yanıt) > 100 else "")
        await respond(interaction,
            c_container(
                c_text(
                    f"**✅ Komut Oluşturuldu**\n\n"
                    f"**İsim:** `{isim}`\n"
                    f"**Kullanım:** `/komut isim:{isim}`\n"
                    f"**Yanıt Önizleme:**\n{preview}"
                ),
                color=0x57F287,
            ),
            ephemeral=True,
        )

    # /komut-liste
    @app_commands.command(name="komut-liste", description="Sunucudaki özel komutları listeler.")
    async def komut_liste(self, interaction: discord.Interaction):
        rows = await db.list_custom_commands(interaction.guild_id)
        if not rows:
            return await respond(interaction,
                c_container(c_text("**📋 Özel Komutlar**\n\nBu sunucuda henüz özel komut oluşturulmamış.\n`/komut-yarat` ile ekleyebilirsiniz."), color=0xF0A030),
                ephemeral=True,
            )

        lines = [f"**📋 Özel Komutlar — {len(rows)} adet**", ""]
        for row in rows[:25]:
            preview = row["response"][:80] + "..." if len(row["response"]) > 80 else row["response"]
            lines.append(f"🔸 `/{row['name']}` — {preview}")
        if len(rows) > 25:
            lines.append(f"\n-# İlk 25 komut gösteriliyor, toplam {len(rows)}")

        await respond(interaction,
            c_container(c_text("\n".join(lines)), color=0x5865F2),
            ephemeral=True,
        )

    # /komut-sil
    @app_commands.command(name="komut-sil", description="Bir özel komutu siler.")
    @app_commands.describe(isim="Silinecek komutun ismi")
    async def komut_sil(self, interaction: discord.Interaction, isim: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await respond(interaction,
                c_container(c_text("**❌ Yetersiz Yetki**\n\nBu komut için **Sunucuyu Yönet** yetkisi gereklidir."), color=0xED4245),
                ephemeral=True,
            )
        isim = isim.lower().strip()
        if await db.delete_custom_command(interaction.guild_id, isim):
            await respond(interaction,
                c_container(c_text(f"**🗑️ Komut Silindi**\n\n`{isim}` komutu başarıyla silindi."), color=0x57F287),
                ephemeral=True,
            )
        else:
            await respond(interaction,
                c_container(c_text(f"**❌ Bulunamadı**\n\n`{isim}` adında bir komut bulunamadı."), color=0xED4245),
                ephemeral=True,
            )

    # /komut
    @app_commands.command(name="komut", description="Bir özel komutu çalıştırır.")
    @app_commands.describe(isim="Çalıştırılacak komutun ismi")
    async def komut(self, interaction: discord.Interaction, isim: str):
        isim = isim.lower().strip()
        row  = await db.get_custom_command(interaction.guild_id, isim)
        if not row:
            return await respond(interaction,
                c_container(c_text(f"**❌ Bulunamadı**\n\n`{isim}` adında bir komut yok.\n`/komut-liste` ile mevcut komutları görebilirsiniz."), color=0xED4245),
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
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(
            embed=discord.Embed(title="❌ Hata", description=str(error), color=discord.Color.red()),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(CustomCommands(bot))
