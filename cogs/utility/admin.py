import discord
from discord import app_commands
from discord.ext import commands
import os
import sys
from ._shared import _emb


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /yardım
    @app_commands.command(name="yardım", description="Tüm komutları listeler.")
    async def yardım(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🐓 Horoz Bot — Komut Listesi", color=discord.Color.blurple())
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(
            name="👤 /üye",
            value="`uyar` `at` `yasakla` `sustur` `sus-kaldır`",
            inline=False,
        )
        embed.add_field(
            name="🔒 /kanal",
            value="`temizle` `yavaşmod` `kilitle` `kilit-aç`",
            inline=False,
        )
        embed.add_field(
            name="⚠️ /ihlal",
            value="`listele` `sil`",
            inline=False,
        )
        embed.add_field(
            name="🎵 /müzik",
            value="`çal` `ara` `atla` `duraklat` `devam` `dur`\n`ses` `sıra` `sıra-sil` `karıştır` `döngü` `şimdi`",
            inline=False,
        )
        embed.add_field(
            name="🎮 Oyunlar",
            value="`/yazıtura` `/zar` `/8top`",
            inline=False,
        )
        embed.add_field(
            name="📊 Sosyal",
            value="`/anket` `/etkinlik`",
            inline=False,
        )
        embed.add_field(
            name="😀 Emoji & Sticker",
            value="`/emoji-ekle` `/oto-emoji`\nSağ tık → **Emojileri Ekle** | **Sticker'ı Ekle**",
            inline=False,
        )
        embed.add_field(
            name="⚙️ Özel Komutlar",
            value="`/komut-yarat` `/komut-liste` `/komut-sil` `/komut`",
            inline=False,
        )
        embed.add_field(
            name="📢 Yönetim & Yayın",
            value="`/yaz` `/embed` `/duyuru` `/tazele`",
            inline=False,
        )
        embed.add_field(
            name="ℹ️ Araçlar",
            value="`/yardım` `/ping` `/hatırlat` `/profil` `/sunucu` `/avatar` `/bot`",
            inline=False,
        )
        embed.set_footer(text="Horoz Bot | Tüm komutlar slash (/) ile kullanılır.")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # /tazele
    @app_commands.command(name="tazele", description="Slash komutlarını Discord ile senkronize eder (eski komutları siler).")
    @app_commands.checks.has_permissions(administrator=True)
    async def tazele(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.bot.tree.clear_commands(guild=interaction.guild)
        await self.bot.tree.sync(guild=interaction.guild)
        synced = await self.bot.tree.sync()
        await interaction.followup.send(
            embed=_emb(
                "✅ Komutlar Tazelendi",
                f"**{len(synced)}** global slash komutu senkronize edildi.\nSunucuya özel eski komutlar temizlendi.",
                discord.Color.green(),
            ),
            ephemeral=True,
        )

    # /restart
    @app_commands.command(name="restart", description="Botu yeniden başlatır ve komutları tazeler.")
    @app_commands.checks.has_permissions(administrator=True)
    async def restart(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=_emb("🔄 Yeniden Başlatılıyor...", "Bot kapatılıyor, birkaç saniye sonra geri dönecek.", discord.Color.orange()),
            ephemeral=True,
        )
        await self.bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg  = "Bu komutu kullanmak için **Yönetici** yetkisi gereklidir." if isinstance(error, app_commands.MissingPermissions) else str(error)
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(embed=_emb("❌ Hata", msg, discord.Color.red()), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
