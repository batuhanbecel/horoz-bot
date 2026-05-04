import discord
from discord import app_commands
from discord.ext import commands
import re
import aiohttp
from database import db

EMOJI_RE = re.compile(r"<(a?):(\w+):(\d+)>")


def _emb(title: str, desc: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text="Horoz Bot • Emoji")
    e.timestamp = discord.utils.utcnow()
    return e


async def fetch_bytes(url: str) -> bytes | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                return await r.read() if r.status == 200 else None
    except Exception:
        return None


class EmojiStealer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ctx_emoji = app_commands.ContextMenu(name="Emojileri Ekle", callback=self._ctx_emoji_ekle)
        bot.tree.add_command(self._ctx_emoji)

    async def cog_unload(self):
        self.bot.tree.remove_command(self._ctx_emoji.name, type=self._ctx_emoji.type)

    # /emoji-ekle
    @app_commands.command(name="emoji-ekle", description="Başka bir sunucudaki özel emojiyi bu sunucuya ekler.")
    @app_commands.describe(emoji="Emoji metni  (<:isim:123456>  veya  <a:isim:123456>)")
    async def emoji_ekle(self, interaction: discord.Interaction, emoji: str):
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.manage_emojis_and_stickers:
            return await interaction.followup.send(
                embed=_emb("❌ Yetersiz Yetki", "Bu komut için **Emojileri Yönet** yetkisi gereklidir.", discord.Color.red()),
                ephemeral=True,
            )

        match = EMOJI_RE.search(emoji)
        if not match:
            return await interaction.followup.send(
                embed=_emb("❌ Geçersiz Emoji", "Özel emoji formatında girin.\nÖrn: `<:isim:123456>` veya `<a:isim:123456>`", discord.Color.red()),
                ephemeral=True,
            )

        animated, name, emoji_id = match.groups()
        ext  = "gif" if animated else "png"
        data = await fetch_bytes(f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}")

        if not data:
            return await interaction.followup.send(
                embed=_emb("❌ İndirme Hatası", "Emoji CDN'den indirilemedi.", discord.Color.red()),
                ephemeral=True,
            )

        try:
            new_e = await interaction.guild.create_custom_emoji(name=name, image=data)
            embed = _emb("✅ Emoji Eklendi", f"{new_e}  **:{new_e.name}:**  sunucuya eklendi!", discord.Color.green())
            embed.add_field(name="İsim",      value=f"`{new_e.name}`",               inline=True)
            embed.add_field(name="ID",        value=f"`{new_e.id}`",                 inline=True)
            embed.add_field(name="Animasyon", value="Evet" if animated else "Hayır", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.HTTPException as ex:
            await interaction.followup.send(
                embed=_emb("❌ Hata", f"Emoji eklenemedi:\n```{ex}```", discord.Color.red()), ephemeral=True
            )

    # /oto-emoji
    @app_commands.command(name="oto-emoji", description="Sunucuda kullanılan yabancı emojileri otomatik ekler (aç/kapat).")
    async def oto_emoji(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.manage_emojis_and_stickers:
            return await interaction.followup.send(
                embed=_emb("❌ Yetersiz Yetki", "Bu komut için **Emojileri Yönet** yetkisi gereklidir.", discord.Color.red()),
                ephemeral=True,
            )

        current = await db.get_setting(interaction.guild_id, "auto_emoji")
        new_val = "0" if current == "1" else "1"
        await db.set_setting(interaction.guild_id, "auto_emoji", new_val)

        if new_val == "1":
            embed = _emb("✅ Otomatik Emoji Açıldı",
                          "Artık sunucuda kullanılan yabancı emojiler otomatik olarak eklenir.\n"
                          "⚠️ Emoji limiti dolduğunda yeni eklemeler atlanır.",
                          discord.Color.green())
        else:
            embed = _emb("⏹️ Otomatik Emoji Kapatıldı", "Artık otomatik emoji ekleme yapılmayacak.", discord.Color.orange())
        await interaction.followup.send(embed=embed, ephemeral=True)

    # Sağ tık → Emojileri Ekle
    async def _ctx_emoji_ekle(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        try:
            if not interaction.user.guild_permissions.manage_emojis_and_stickers:
                return await interaction.followup.send(
                    embed=_emb("❌ Yetersiz Yetki", "Bu işlem için **Emojileri Yönet** yetkisi gereklidir.", discord.Color.red()),
                    ephemeral=True,
                )

            guild_emoji_ids = {str(em.id) for em in interaction.guild.emojis}
            matches = [
                (a, n, i) for a, n, i in EMOJI_RE.findall(message.content)
                if i not in guild_emoji_ids
            ]

            if not matches:
                return await interaction.followup.send(
                    embed=_emb("⚠️ Emoji Bulunamadı", "Bu mesajda bu sunucuya ait olmayan özel emoji yok.", discord.Color.orange()),
                    ephemeral=True,
                )

            added, failed = [], []
            for animated, name, emoji_id in matches[:10]:
                ext  = "gif" if animated else "png"
                data = await fetch_bytes(f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}")
                if not data:
                    failed.append(name)
                    continue
                try:
                    em = await interaction.guild.create_custom_emoji(name=name, image=data)
                    added.append(str(em))
                except discord.HTTPException:
                    failed.append(name)

            lines = []
            if added:  lines.append(f"✅ **Eklendi ({len(added)}):** {' '.join(added)}")
            if failed: lines.append(f"❌ **Başarısız ({len(failed)}):** {', '.join(f'`{n}`' for n in failed)}")
            color = discord.Color.green() if added else discord.Color.red()
            await interaction.followup.send(
                embed=_emb("Emoji Ekleme Sonucu", "\n".join(lines) or "Hiçbir emoji eklenemedi.", color),
                ephemeral=True,
            )
        except Exception as ex:
            await interaction.followup.send(
                embed=_emb("❌ Hata", str(ex), discord.Color.red()), ephemeral=True
            )

    # on_message: otomatik emoji
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content:
            return
        try:
            auto = await db.get_setting(message.guild.id, "auto_emoji")
            if auto != "1":
                return
            guild_emoji_ids = {str(em.id) for em in message.guild.emojis}
            matches = [
                (a, n, i) for a, n, i in EMOJI_RE.findall(message.content)
                if i not in guild_emoji_ids
            ]
            if not matches:
                return
            animated, name, emoji_id = matches[0]
            ext  = "gif" if animated else "png"
            data = await fetch_bytes(f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}")
            if data:
                await message.guild.create_custom_emoji(name=name, image=data)
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(EmojiStealer(bot))
