import discord
from discord import app_commands
from discord.ext import commands
from database import db
from .._v2 import (
    COLORS, c_card, c_action_card, c_list_card, respond, error_response,
)


class CustomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /komut-yarat
    @app_commands.command(name="komut-yarat", description="Sunucuya özel bir komut oluşturur.")
    @app_commands.describe(
        isim="Komut ismi (boşluksuz, küçük harf, max 32 karakter)",
        yanıt="Komut çalıştırıldığında gönderilecek mesaj",
    )
    @app_commands.guild_only()
    async def komut_yarat(self, interaction: discord.Interaction, isim: str, yanıt: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="Bu komut için **Sunucuyu Yönet** yetkisi gereklidir."),
                ephemeral=True,
            )

        isim = isim.lower().strip().replace(" ", "-")
        if not (2 <= len(isim) <= 32):
            return await respond(interaction,
                c_card("## ❌ Geçersiz İsim", body="Komut ismi **2–32** karakter arasında olmalıdır."),
                ephemeral=True,
            )

        if await db.get_custom_command(interaction.guild_id, isim):
            return await respond(interaction,
                c_card("## ❌ Zaten Mevcut", body=f"`{isim}` adında bir komut zaten var.\n`/komut-sil` ile önce silebilirsiniz."),
                ephemeral=True,
            )

        await db.create_custom_command(interaction.guild_id, isim, yanıt, interaction.user.id)
        preview = yanıt[:120] + ("..." if len(yanıt) > 120 else "")

        await respond(interaction, c_action_card(
            "✅ Özel Komut Oluşturuldu",
            fields=[
                ("📛 İsim", f"`/{isim}`"),
                ("🔑 Kullanım", f"`/komut isim:{isim}`"),
                ("👤 Sahibi", interaction.user.mention),
                ("📝 Önizleme", f"```\n{preview}\n```"),
            ],
            footer="Komutu /komut-liste ile görebilirsin.",
        ), ephemeral=True)

    # /komut-liste
    @app_commands.command(name="komut-liste", description="Sunucudaki özel komutları listeler.")
    @app_commands.guild_only()
    async def komut_liste(self, interaction: discord.Interaction):
        rows = await db.list_custom_commands(interaction.guild_id)
        if not rows:
            return await respond(interaction,
                c_card(
                    "## 📋 Özel Komutlar",
                    body="Bu sunucuda henüz özel komut yok.\n`/komut-yarat` ile oluşturabilirsin.",
                ),
                ephemeral=True,
            )

        rows_out: list[str] = []
        for row in rows[:25]:
            preview = row["response"][:60] + ("..." if len(row["response"]) > 60 else "")
            rows_out.append(f"🔸 **`/{row['name']}`**\n┗ `{preview}`")

        footer = (
            f"Toplam {len(rows)} komut · İlk 25 gösteriliyor"
            if len(rows) > 25 else f"Toplam {len(rows)} komut"
        )

        await respond(interaction, c_list_card(
            f"📋 Özel Komutlar — {interaction.guild.name}",
            rows=rows_out,
            footer=footer,
        ), ephemeral=True)

    # /komut-sil
    @app_commands.command(name="komut-sil", description="Bir özel komutu siler.")
    @app_commands.describe(isim="Silinecek komutun ismi")
    @app_commands.guild_only()
    async def komut_sil(self, interaction: discord.Interaction, isim: str):
        if not interaction.user.guild_permissions.manage_guild:
            return await respond(interaction,
                c_card("## ❌ Yetersiz Yetki", body="Bu komut için **Sunucuyu Yönet** yetkisi gereklidir."),
                ephemeral=True,
            )
        isim = isim.lower().strip()
        if await db.delete_custom_command(interaction.guild_id, isim):
            await respond(interaction, c_action_card(
                "🗑️ Komut Silindi",
                fields=[
                    ("📛 İsim", f"`/{isim}`"),
                    ("👮 Silen", interaction.user.mention),
                ],
            ), ephemeral=True)
        else:
            await respond(interaction,
                c_card("## ❌ Bulunamadı", body=f"`{isim}` adında bir komut bulunamadı."),
                ephemeral=True,
            )

    # /komut
    @app_commands.command(name="komut", description="Bir özel komutu çalıştırır.")
    @app_commands.describe(isim="Çalıştırılacak komutun ismi")
    @app_commands.guild_only()
    async def komut(self, interaction: discord.Interaction, isim: str):
        isim = isim.lower().strip()
        row  = await db.get_custom_command(interaction.guild_id, isim)
        if not row:
            return await respond(interaction,
                c_card(
                    "## ❌ Bulunamadı",
                    body=f"`{isim}` adında bir komut yok.\n`/komut-liste` ile mevcut komutları görebilirsin.",
                ),
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
        await error_response(interaction, str(error))


async def setup(bot: commands.Bot):
    await bot.add_cog(CustomCommands(bot))
