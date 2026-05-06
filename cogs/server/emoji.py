import discord
from discord import app_commands
from discord.ext import commands
import re
import aiohttp
from database import db
from .._v2 import (
    COLORS, c_card, c_action_card, c_list_card, c_text, c_section, c_thumbnail, c_separator, c_container,
    respond, followup as v2_followup,
)

EMOJI_RE = re.compile(r"<(a?):(\w+):(\d+)>")


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

    # /emoji-ekle ─ tek emoji ekleme
    @app_commands.command(name="emoji-ekle", description="Başka bir sunucudaki özel emojiyi bu sunucuya ekler.")
    @app_commands.describe(emoji="Emoji metni  (<:isim:123456>  veya  <a:isim:123456>)")
    async def emoji_ekle(self, interaction: discord.Interaction, emoji: str):
        await interaction.response.defer(ephemeral=True)
        thumb = str(interaction.client.user.display_avatar.url)

        if not interaction.user.guild_permissions.manage_emojis_and_stickers:
            return await v2_followup(interaction,
                c_card("## ❌ Yetersiz Yetki", body="Bu komut için **Emojileri Yönet** yetkisi gereklidir.", thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
            )

        match = EMOJI_RE.search(emoji)
        if not match:
            return await v2_followup(interaction,
                c_card(
                    "## ❌ Geçersiz Emoji",
                    body="Özel emoji formatında girin:\n`<:isim:123456>` veya `<a:isim:123456>`",
                    thumbnail=thumb,
                    color=COLORS.DANGER,
                ),
                ephemeral=True,
            )

        animated, name, emoji_id = match.groups()
        ext  = "gif" if animated else "png"
        emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
        data = await fetch_bytes(emoji_url)

        if not data:
            return await v2_followup(interaction,
                c_card("## ❌ İndirme Hatası", body="Emoji CDN'den indirilemedi.", thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
            )

        try:
            new_e = await interaction.guild.create_custom_emoji(name=name, image=data)
            slot_kullanim = f"`{len(interaction.guild.emojis)}/{interaction.guild.emoji_limit}`"
            await v2_followup(interaction, c_action_card(
                "✅ Emoji Eklendi",
                target_avatar=emoji_url,
                fields=[
                    ("✨ Emoji", f"{new_e}  `:{new_e.name}:`"),
                    ("🆔 ID", f"`{new_e.id}`"),
                    ("🎬 Animasyon", "Evet" if animated else "Hayır"),
                    ("📊 Slot Kullanımı", slot_kullanim),
                ],
                color=COLORS.SUCCESS,
            ), ephemeral=True)
        except discord.HTTPException as ex:
            await v2_followup(interaction,
                c_card("## ❌ Hata", body=f"Emoji eklenemedi:\n```{ex}```", thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
            )

    # /oto-emoji ─ otomatik ekleme aç/kapa
    @app_commands.command(name="oto-emoji", description="Sunucuda kullanılan yabancı emojileri otomatik ekler (aç/kapat).")
    async def oto_emoji(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        thumb = str(interaction.client.user.display_avatar.url)
        if not interaction.user.guild_permissions.manage_emojis_and_stickers:
            return await v2_followup(interaction,
                c_card("## ❌ Yetersiz Yetki", body="Bu komut için **Emojileri Yönet** yetkisi gereklidir.", thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
            )

        current = await db.get_setting(interaction.guild_id, "auto_emoji")
        new_val = "0" if current == "1" else "1"
        await db.set_setting(interaction.guild_id, "auto_emoji", new_val)

        if new_val == "1":
            await v2_followup(interaction, c_action_card(
                "✅ Otomatik Emoji Açıldı",
                target_avatar=thumb,
                fields=[
                    ("⚙️ Durum", "🟢 Açık"),
                    ("📊 Slot", f"`{len(interaction.guild.emojis)}/{interaction.guild.emoji_limit}`"),
                    ("👮 Yetkili", interaction.user.mention),
                ],
                footer="⚠️ Emoji limiti dolduğunda yeni eklemeler atlanır.",
                color=COLORS.SUCCESS,
            ), ephemeral=True)
        else:
            await v2_followup(interaction, c_action_card(
                "⏹️ Otomatik Emoji Kapatıldı",
                target_avatar=thumb,
                fields=[
                    ("⚙️ Durum", "🔴 Kapalı"),
                    ("👮 Yetkili", interaction.user.mention),
                ],
                color=COLORS.WARNING,
            ), ephemeral=True)

    # Sağ tık → Emojileri Ekle
    async def _ctx_emoji_ekle(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral=True)
        thumb = str(interaction.client.user.display_avatar.url)
        try:
            if not interaction.user.guild_permissions.manage_emojis_and_stickers:
                return await v2_followup(interaction,
                    c_card("## ❌ Yetersiz Yetki", body="Bu işlem için **Emojileri Yönet** yetkisi gereklidir.", thumbnail=thumb, color=COLORS.DANGER),
                    ephemeral=True,
                )

            guild_emoji_ids = {str(em.id) for em in interaction.guild.emojis}
            matches = [
                (a, n, i) for a, n, i in EMOJI_RE.findall(message.content)
                if i not in guild_emoji_ids
            ]

            if not matches:
                return await v2_followup(interaction,
                    c_card("## ⚠️ Emoji Bulunamadı", body="Bu mesajda bu sunucuya ait olmayan özel emoji yok.", thumbnail=thumb, color=COLORS.WARNING),
                    ephemeral=True,
                )

            added: list[str] = []
            failed: list[str] = []
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

            rows: list[str] = []
            if added:
                rows.append(f"**✅ Eklenen ({len(added)})**\n{' '.join(added)}")
            if failed:
                rows.append(f"**❌ Başarısız ({len(failed)})**\n{', '.join(f'`{n}`' for n in failed)}")
            color = COLORS.SUCCESS if added else COLORS.DANGER

            await v2_followup(interaction, c_list_card(
                "✨ Emoji Ekleme Sonucu",
                rows=rows or ["Hiçbir emoji eklenemedi."],
                thumbnail=thumb,
                footer=f"Slot: {len(interaction.guild.emojis)}/{interaction.guild.emoji_limit}",
                color=color,
            ), ephemeral=True)
        except Exception as ex:
            await v2_followup(interaction,
                c_card("## ❌ Hata", body=str(ex), thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
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
