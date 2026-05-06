import discord
from discord import app_commands
from discord.ext import commands
import io
import aiohttp
from .._v2 import c_text, c_section, c_container, c_thumbnail, followup as v2_followup


async def fetch_bytes(url: str) -> bytes | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                return await r.read() if r.status == 200 else None
    except Exception:
        return None


class StickerStealer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ctx_sticker = app_commands.ContextMenu(name="Sticker'ı Ekle", callback=self._ctx_sticker_ekle)
        bot.tree.add_command(self._ctx_sticker)

    async def cog_unload(self):
        self.bot.tree.remove_command(self._ctx_sticker.name, type=self._ctx_sticker.type)

    async def _ctx_sticker_ekle(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        try:
            if not interaction.user.guild_permissions.manage_emojis_and_stickers:
                return await v2_followup(interaction,
                    c_container(c_text("**❌ Yetersiz Yetki**\n\nBu işlem için **Emojileri Yönet** yetkisi gereklidir."), color=0xED4245),
                    ephemeral=True,
                )
            if not message.stickers:
                return await v2_followup(interaction,
                    c_container(c_text("**⚠️ Sticker Bulunamadı**\n\nBu mesajda sticker yok."), color=0xE67E22),
                    ephemeral=True,
                )

            sticker = await message.stickers[0].fetch()

            if sticker.format == discord.StickerFormatType.lottie:
                return await v2_followup(interaction,
                    c_container(c_text("**⚠️ Desteklenmiyor**\n\nLottie animasyonlu sticker'lar eklenemez."), color=0xE67E22),
                    ephemeral=True,
                )

            ext  = "gif" if sticker.format == discord.StickerFormatType.gif else "png"
            data = await fetch_bytes(str(sticker.url))
            if not data:
                return await v2_followup(interaction,
                    c_container(c_text("**❌ İndirme Hatası**\n\nSticker indirilemedi."), color=0xED4245),
                    ephemeral=True,
                )

            new_s = await interaction.guild.create_sticker(
                name=sticker.name,
                description=sticker.description or sticker.name,
                emoji="⭐",
                file=discord.File(io.BytesIO(data), filename=f"sticker.{ext}"),
            )
            await v2_followup(interaction,
                c_container(
                    c_section(
                        c_text(
                            f"**✅ Sticker Eklendi**\n\n"
                            f"**{new_s.name}** sunucuya eklendi!\n"
                            f"🆔 **ID:** `{new_s.id}`"
                        ),
                        accessory=c_thumbnail(str(sticker.url)),
                    ),
                    color=0x57F287,
                ),
                ephemeral=True,
            )

        except discord.HTTPException as ex:
            await v2_followup(interaction,
                c_container(c_text(f"**❌ Hata**\n\n{ex}"), color=0xED4245),
                ephemeral=True,
            )
        except Exception as ex:
            await v2_followup(interaction,
                c_container(c_text(f"**❌ Hata**\n\n{ex}"), color=0xED4245),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(StickerStealer(bot))
