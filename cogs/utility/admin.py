import discord
from discord import app_commands
from discord.ext import commands
import os
import sys
from .._v2 import (
    COLORS, c_card, c_info_card, c_text, c_separator, c_container,
    respond, followup as v2_followup, error_response,
)


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /yardım ─ kategorize edilmiş komut menüsü
    @app_commands.command(name="yardım", description="Tüm komutları listeler.")
    async def yardım(self, interaction: discord.Interaction):
        moderation = (
            "**👤 /üye** · `uyar` `at` `yasakla` `sustur` `sus-kaldır`\n"
            "**🔒 /kanal** · `temizle` `yavaşmod` `kilitle` `kilit-aç`\n"
            "**⚠️ /ihlal** · `listele` `sil`"
        )
        music = (
            "**🎵 /müzik** · `çal` `ara` `atla` `duraklat` `devam` `dur`\n"
            "                 `ses` `sıra` `sıra-sil` `karıştır` `döngü` `şimdi`"
        )
        games = (
            "**🎮 Oyunlar**\n"
            "`/yazıtura` `/zar` `/8top` `/kaccm` `/tkm`\n"
            "`/adamasmaca` `/arena` `/isimşehir` `/vampirkoylu` `/rusruleti`"
        )
        social = "**📊 Sosyal** · `/anket` `/etkinlik`"
        emoji = (
            "**😀 Emoji & Sticker** · `/emoji-ekle` `/oto-emoji`\n"
            "-# Sağ tık → **Emojileri Ekle** · **Sticker'ı Ekle**"
        )
        custom = "**⚙️ Özel Komutlar** · `/komut-yarat` `/komut-liste` `/komut-sil` `/komut`"
        publish = "**📢 Yayın** · `/yaz` `/embed` `/duyuru`"
        admin = "**🛠️ Yönetim** · `/tazele` `/restart`"
        tools = "**ℹ️ Araçlar** · `/yardım` `/ping` `/hatırlat` `/profil` `/sunucu` `/avatar` `/bot`"

        await respond(interaction, c_info_card(
            "🐓 Horoz Bot — Komut Listesi",
            groups=[
                moderation,
                music,
                games,
                social + "\n" + emoji,
                custom,
                publish + "\n" + admin,
                tools,
            ],
            footer="Tüm komutlar slash (/) ile kullanılır · Components V2",
            color=COLORS.PRIMARY,
        ), ephemeral=True)

    # /tazele
    @app_commands.command(name="tazele", description="Slash komutlarını Discord ile senkronize eder (eski komutları siler).")
    @app_commands.checks.has_permissions(administrator=True)
    async def tazele(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.bot.tree.clear_commands(guild=interaction.guild)
        await self.bot.tree.sync(guild=interaction.guild)
        synced = await self.bot.tree.sync()

        await v2_followup(interaction, c_container(
            c_text("## ✅ Komutlar Tazelendi"),
            c_separator(),
            c_text(
                f"🌐 **Global Komut:** `{len(synced)}` adet senkronize edildi\n"
                f"🧹 **Sunucuya Özel:** Eski komutlar temizlendi\n"
                f"🛡️ **Yetkili:** {interaction.user.mention}"
            ),
            c_separator(),
            c_text("-# Komutların görünmesi 1-2 dakika sürebilir."),
            color=COLORS.SUCCESS,
        ), ephemeral=True)

    # /restart
    @app_commands.command(name="restart", description="Botu yeniden başlatır ve komutları tazeler.")
    @app_commands.checks.has_permissions(administrator=True)
    async def restart(self, interaction: discord.Interaction):
        await respond(interaction, c_container(
            c_text("## 🔄 Yeniden Başlatılıyor..."),
            c_separator(),
            c_text(
                f"⏳ Bot kapatılıyor, birkaç saniye sonra geri dönecek.\n"
                f"🛡️ **Yetkili:** {interaction.user.mention}"
            ),
            color=COLORS.WARNING,
        ), ephemeral=True)
        await self.bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Bu komutu kullanmak için **Yönetici** yetkisi gereklidir." \
            if isinstance(error, app_commands.MissingPermissions) else str(error)
        await error_response(interaction, msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
