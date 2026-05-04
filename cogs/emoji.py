import discord
from discord import app_commands
from discord.ext import commands
import re
import io
import aiohttp
from database import db

EMOJI_RE = re.compile(r"<(a?):(\w+):(\d+)>")


def e_embed(title: str, desc: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    emb = discord.Embed(title=title, description=desc, color=color)
    emb.timestamp = discord.utils.utcnow()
    return emb


async def fetch_bytes(url: str) -> bytes | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read() if resp.status == 200 else None


class EmojiStealer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ctx_emoji = app_commands.ContextMenu(
            name="Emojileri Ekle",
            callback=self._ctx_emoji_ekle,
        )
        self._ctx_sticker = app_commands.ContextMenu(
            name="Sticker'ı Ekle",
            callback=self._ctx_sticker_ekle,
        )
        bot.tree.add_command(self._ctx_emoji)
        bot.tree.add_command(self._ctx_sticker)

    async def cog_unload(self):
        self.bot.tree.remove_command(self._ctx_emoji.name, type=self._ctx_emoji.type)
        self.bot.tree.remove_command(self._ctx_sticker.name, type=self._ctx_sticker.type)

    # ── /emoji-çal ────────────────────────────────────────────────────────────

    @app_commands.command(name="emoji-çal", description="Özel bir emojiyi bu sunucuya kopyalar.")
    @app_commands.describe(emoji="Emoji (örn: <:isim:123456> veya <a:isim:123456>)")
    @app_commands.checks.has_permissions(manage_emojis_and_stickers=True)
    async def emoji_cal(self, interaction: discord.Interaction, emoji: str):
        await interaction.response.defer(ephemeral=True)
        match = EMOJI_RE.search(emoji)
        if not match:
            return await interaction.followup.send(
                embed=e_embed("Hata", "Geçerli özel emoji girin.\nÖrn: `<:isim:123456>` veya `<a:isim:123456>`", discord.Color.red()),
                ephemeral=True,
            )
        animated, name, emoji_id = match.groups()
        ext = "gif" if animated else "png"
        data = await fetch_bytes(f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}")
        if not data:
            return await interaction.followup.send(
                embed=e_embed("Hata", "Emoji indirilemedi.", discord.Color.red()), ephemeral=True
            )
        try:
            new_e = await interaction.guild.create_custom_emoji(name=name, image=data)
            await interaction.followup.send(
                embed=e_embed("Emoji Eklendi", f"{new_e} `:{new_e.name}:` başarıyla eklendi!", discord.Color.green()),
                ephemeral=True,
            )
        except discord.HTTPException as ex:
            await interaction.followup.send(
                embed=e_embed("Hata", str(ex), discord.Color.red()), ephemeral=True
            )

    # ── /emoji-otomatik ───────────────────────────────────────────────────────

    @app_commands.command(
        name="emoji-otomatik",
        description="Sunucuda kullanılan yabancı emojileri otomatik olarak ekler (aç/kapat).",
    )
    @app_commands.checks.has_permissions(manage_emojis_and_stickers=True)
    async def emoji_otomatik(self, interaction: discord.Interaction):
        current = await db.get_setting(interaction.guild_id, "auto_emoji")
        new_val = "0" if current == "1" else "1"
        await db.set_setting(interaction.guild_id, "auto_emoji", new_val)
        durum = "**açıldı** ✅" if new_val == "1" else "**kapatıldı** ❌"
        await interaction.response.send_message(
            embed=e_embed(
                "Otomatik Emoji",
                f"Otomatik emoji ekleme {durum}.\n"
                + ("Artık yabancı emojiler kullanıldığında otomatik eklenecek." if new_val == "1"
                   else "Artık otomatik ekleme yapılmayacak."),
                discord.Color.green(),
            ),
            ephemeral=True,
        )

    # ── Sağ tık → Emojileri Ekle ─────────────────────────────────────────────

    async def _ctx_emoji_ekle(self, interaction: discord.Interaction, message: discord.Message):
        if not interaction.user.guild_permissions.manage_emojis_and_stickers:
            return await interaction.response.send_message(
                embed=e_embed("Hata", "`Emojileri Yönet` yetkisi gereklidir.", discord.Color.red()),
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True)

        guild_emoji_ids = {str(em.id) for em in interaction.guild.emojis}
        matches = [
            (a, n, i)
            for a, n, i in EMOJI_RE.findall(message.content)
            if i not in guild_emoji_ids
        ]

        if not matches:
            return await interaction.followup.send(
                embed=e_embed("Bulunamadı", "Mesajda bu sunucuya ait olmayan özel emoji yok.", discord.Color.orange()),
                ephemeral=True,
            )

        added, failed = [], []
        for animated, name, emoji_id in matches[:10]:
            ext = "gif" if animated else "png"
            data = await fetch_bytes(f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}")
            if not data:
                failed.append(name)
                continue
            try:
                em = await interaction.guild.create_custom_emoji(name=name, image=data)
                added.append(str(em))
            except discord.HTTPException:
                failed.append(name)

        desc = ""
        if added:
            desc += f"✅ Eklendi: {' '.join(added)}\n"
        if failed:
            desc += f"❌ Eklenemedi: {', '.join(f'`{n}`' for n in failed)}"
        color = discord.Color.green() if added else discord.Color.red()
        await interaction.followup.send(
            embed=e_embed("Emoji Ekleme Sonucu", desc or "Hiçbir emoji eklenemedi.", color),
            ephemeral=True,
        )

    # ── Sağ tık → Sticker'ı Ekle ─────────────────────────────────────────────

    async def _ctx_sticker_ekle(self, interaction: discord.Interaction, message: discord.Message):
        if not interaction.user.guild_permissions.manage_emojis_and_stickers:
            return await interaction.response.send_message(
                embed=e_embed("Hata", "`Emojileri Yönet` yetkisi gereklidir.", discord.Color.red()),
                ephemeral=True,
            )
        if not message.stickers:
            return await interaction.response.send_message(
                embed=e_embed("Bulunamadı", "Bu mesajda sticker bulunamadı.", discord.Color.orange()),
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True)

        sticker_item = message.stickers[0]
        try:
            sticker = await sticker_item.fetch()
        except discord.HTTPException:
            return await interaction.followup.send(
                embed=e_embed("Hata", "Sticker bilgisi alınamadı.", discord.Color.red()), ephemeral=True
            )

        if sticker.format == discord.StickerFormatType.lottie:
            return await interaction.followup.send(
                embed=e_embed("Desteklenmiyor", "Lottie animasyonlu sticker'lar bot tarafından eklenemez.", discord.Color.orange()),
                ephemeral=True,
            )

        ext = "gif" if sticker.format == discord.StickerFormatType.gif else "png"
        data = await fetch_bytes(str(sticker.url))
        if not data:
            return await interaction.followup.send(
                embed=e_embed("Hata", "Sticker indirilemedi.", discord.Color.red()), ephemeral=True
            )

        try:
            new_s = await interaction.guild.create_sticker(
                name=sticker.name,
                description=sticker.description or sticker.name,
                emoji="⭐",
                file=discord.File(io.BytesIO(data), filename=f"sticker.{ext}"),
            )
            await interaction.followup.send(
                embed=e_embed("Sticker Eklendi", f"**{new_s.name}** başarıyla eklendi!", discord.Color.green()),
                ephemeral=True,
            )
        except discord.HTTPException as ex:
            await interaction.followup.send(
                embed=e_embed("Hata", str(ex), discord.Color.red()), ephemeral=True
            )

    # ── on_message: Otomatik emoji ────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content:
            return
        auto = await db.get_setting(message.guild.id, "auto_emoji")
        if auto != "1":
            return

        guild_emoji_ids = {str(em.id) for em in message.guild.emojis}
        matches = [
            (a, n, i)
            for a, n, i in EMOJI_RE.findall(message.content)
            if i not in guild_emoji_ids
        ]
        if not matches:
            return

        # Her mesajda en fazla 1 emoji ekle — flood ve limit koruması
        animated, name, emoji_id = matches[0]
        ext = "gif" if animated else "png"
        data = await fetch_bytes(f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}")
        if data:
            try:
                await message.guild.create_custom_emoji(name=name, image=data)
            except discord.HTTPException:
                pass

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Bu işlem için `Emojileri Yönet` yetkisi gereklidir." \
            if isinstance(error, app_commands.MissingPermissions) else str(error)
        if interaction.response.is_done():
            await interaction.followup.send(embed=e_embed("Hata", msg, discord.Color.red()), ephemeral=True)
        else:
            await interaction.response.send_message(embed=e_embed("Hata", msg, discord.Color.red()), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(EmojiStealer(bot))
