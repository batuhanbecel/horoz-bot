import discord
from discord import app_commands
from discord.ext import commands
import io
import aiohttp


async def fetch_bytes(url: str) -> bytes | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                return await r.read() if r.status == 200 else None
    except Exception:
        return None


def _emb(title: str, desc: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text="Horoz Bot • Emoji")
    e.timestamp = discord.utils.utcnow()
    return e


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
                return await interaction.followup.send(
                    embed=_emb("❌ Yetersiz Yetki", "Bu işlem için **Emojileri Yönet** yetkisi gereklidir.", discord.Color.red()),
                    ephemeral=True,
                )
            if not message.stickers:
                return await interaction.followup.send(
                    embed=_emb("⚠️ Sticker Bulunamadı", "Bu mesajda sticker yok.", discord.Color.orange()),
                    ephemeral=True,
                )

            sticker = await message.stickers[0].fetch()

            if sticker.format == discord.StickerFormatType.lottie:
                return await interaction.followup.send(
                    embed=_emb("⚠️ Desteklenmiyor", "Lottie animasyonlu sticker'lar eklenemez.", discord.Color.orange()),
                    ephemeral=True,
                )

            ext  = "gif" if sticker.format == discord.StickerFormatType.gif else "png"
            data = await fetch_bytes(str(sticker.url))
            if not data:
                return await interaction.followup.send(
                    embed=_emb("❌ İndirme Hatası", "Sticker indirilemedi.", discord.Color.red()), ephemeral=True
                )

            new_s = await interaction.guild.create_sticker(
                name=sticker.name,
                description=sticker.description or sticker.name,
                emoji="⭐",
                file=discord.File(io.BytesIO(data), filename=f"sticker.{ext}"),
            )
            embed = _emb("✅ Sticker Eklendi", f"**{new_s.name}** sunucuya eklendi!", discord.Color.green())
            embed.add_field(name="İsim", value=new_s.name,      inline=True)
            embed.add_field(name="ID",   value=str(new_s.id),   inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.HTTPException as ex:
            await interaction.followup.send(
                embed=_emb("❌ Hata", str(ex), discord.Color.red()), ephemeral=True
            )
        except Exception as ex:
            await interaction.followup.send(
                embed=_emb("❌ Hata", str(ex), discord.Color.red()), ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(StickerStealer(bot))
