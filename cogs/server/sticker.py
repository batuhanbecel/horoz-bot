import discord
from discord import app_commands
from discord.ext import commands
import io
import aiohttp
from .._v2 import (
    COLORS, c_card, c_action_card, c_text, c_section, c_thumbnail, c_separator, c_container,
    followup as v2_followup,
)


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
                    c_card("## ❌ Yetersiz Yetki", body="Bu işlem için **Emojileri Yönet** yetkisi gereklidir.", color=COLORS.DANGER),
                    ephemeral=True,
                )
            if not message.stickers:
                return await v2_followup(interaction,
                    c_card("## ⚠️ Sticker Bulunamadı", body="Bu mesajda sticker yok.", color=COLORS.WARNING),
                    ephemeral=True,
                )

            sticker = await message.stickers[0].fetch()

            if sticker.format == discord.StickerFormatType.lottie:
                return await v2_followup(interaction,
                    c_card("## ⚠️ Desteklenmiyor", body="**Lottie** animasyonlu sticker'lar eklenemez.", color=COLORS.WARNING),
                    ephemeral=True,
                )

            ext  = "gif" if sticker.format == discord.StickerFormatType.gif else "png"
            data = await fetch_bytes(str(sticker.url))
            if not data:
                return await v2_followup(interaction,
                    c_card("## ❌ İndirme Hatası", body="Sticker indirilemedi.", color=COLORS.DANGER),
                    ephemeral=True,
                )

            new_s = await interaction.guild.create_sticker(
                name=sticker.name,
                description=sticker.description or sticker.name,
                emoji="⭐",
                file=discord.File(io.BytesIO(data), filename=f"sticker.{ext}"),
            )

            slot = f"`{len(interaction.guild.stickers)}/{interaction.guild.sticker_limit}`"
            await v2_followup(interaction, c_action_card(
                "✅ Sticker Eklendi",
                target_avatar=str(sticker.url),
                fields=[
                    ("🏷️ İsim", f"`{new_s.name}`"),
                    ("🆔 ID", f"`{new_s.id}`"),
                    ("📐 Format", f"`{ext.upper()}`"),
                    ("📊 Slot Kullanımı", slot),
                    ("👮 Ekleyen", interaction.user.mention),
                ],
                color=COLORS.SUCCESS,
            ), ephemeral=True)

        except discord.HTTPException as ex:
            await v2_followup(interaction,
                c_card("## ❌ Hata", body=f"```{ex}```", color=COLORS.DANGER),
                ephemeral=True,
            )
        except Exception as ex:
            await v2_followup(interaction,
                c_card("## ❌ Hata", body=str(ex), color=COLORS.DANGER),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(StickerStealer(bot))
