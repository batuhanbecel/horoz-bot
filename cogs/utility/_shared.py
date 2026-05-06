import discord
from .._v2 import (
    COLORS, c_card, c_action_card, c_text, c_section, c_thumbnail, c_separator, c_container,
    respond, channel_send,
)

RENK_MAP: dict[str, int] = {
    "mavi":    0x3498DB,
    "yesil":   0x2ECC71,
    "kirmizi": 0xED4245,
    "altin":   0xF1C40F,
    "mor":     0x9B59B6,
    "turuncu": 0xE67E22,
    "pembe":   0xFF73FA,
}


class MesajModal(discord.ui.Modal):
    içerik = discord.ui.TextInput(
        label="Mesaj İçeriği",
        style=discord.TextStyle.paragraph,
        placeholder="Göndermek istediğin mesajı buraya yaz...",
        max_length=2000,
    )

    def __init__(self, kanal: discord.TextChannel):
        super().__init__(title="Mesaj Gönder")
        self.kanal = kanal

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.kanal.send(self.içerik.value)
            preview = self.içerik.value[:120] + ("..." if len(self.içerik.value) > 120 else "")
            await respond(interaction, c_action_card(
                "✅ Mesaj Gönderildi",
                fields=[
                    ("📌 Kanal", self.kanal.mention),
                    ("👤 Gönderen", interaction.user.mention),
                    ("📝 Önizleme", f"```{preview}```"),
                ],
                color=COLORS.SUCCESS,
            ), ephemeral=True)
        except discord.Forbidden:
            await respond(interaction,
                c_card("## ❌ Yetki Hatası", body=f"{self.kanal.mention} kanalına yazma iznim yok.", color=COLORS.DANGER),
                ephemeral=True,
            )
        except discord.HTTPException as ex:
            await respond(interaction,
                c_card("## ❌ Hata", body=f"```{ex}```", color=COLORS.DANGER),
                ephemeral=True,
            )


class EmbedModal(discord.ui.Modal):
    başlık_f = discord.ui.TextInput(label="Başlık", placeholder="Embed başlığı", max_length=256)
    içerik_f = discord.ui.TextInput(
        label="İçerik",
        style=discord.TextStyle.paragraph,
        placeholder="Embed metni...",
        max_length=4000,
    )

    def __init__(self, kanal: discord.TextChannel, renk: int):
        super().__init__(title="Embed Mesaj Gönder")
        self.kanal = kanal
        self.renk  = renk

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await channel_send(self.kanal, c_container(
                c_text(f"## {self.başlık_f.value}"),
                c_separator(),
                c_text(self.içerik_f.value),
                c_separator(),
                c_text(f"-# Gönderen: {interaction.user.display_name}"),
                color=self.renk,
            ))
            await respond(interaction, c_action_card(
                "✅ Embed Gönderildi",
                fields=[
                    ("📌 Kanal", self.kanal.mention),
                    ("📰 Başlık", f"`{self.başlık_f.value}`"),
                    ("👤 Gönderen", interaction.user.mention),
                ],
                color=COLORS.SUCCESS,
            ), ephemeral=True)
        except discord.Forbidden:
            await respond(interaction,
                c_card("## ❌ Yetki Hatası", body=f"{self.kanal.mention} kanalına yazma iznim yok.", color=COLORS.DANGER),
                ephemeral=True,
            )
        except discord.HTTPException as ex:
            await respond(interaction,
                c_card("## ❌ Hata", body=f"```{ex}```", color=COLORS.DANGER),
                ephemeral=True,
            )


class DuyuruModal(discord.ui.Modal):
    içerik_f = discord.ui.TextInput(
        label="Duyuru İçeriği",
        style=discord.TextStyle.paragraph,
        placeholder="Duyuru metni...",
        max_length=2000,
    )

    def __init__(self, kanal: discord.TextChannel, ping: str):
        super().__init__(title="Duyuru Gönder")
        self.kanal = kanal
        self.ping  = ping

    async def on_submit(self, interaction: discord.Interaction):
        # Sunucu duyurusunda guild ikonu = içerik bağlamı, kalsın
        guild_icon = str(interaction.guild.icon.url) if interaction.guild and interaction.guild.icon else None
        try:
            duyuru_items: list[dict] = []
            if guild_icon:
                duyuru_items.append(c_section(
                    c_text(f"## 📣 Duyuru\n-# {interaction.guild.name if interaction.guild else ''}"),
                    accessory=c_thumbnail(guild_icon),
                ))
            else:
                duyuru_items.append(c_text(f"## 📣 Duyuru"))
            duyuru_items.extend([
                c_separator(),
                c_text(self.içerik_f.value),
                c_separator(),
                c_text(f"-# 📢 Duyuran: {interaction.user.mention}"),
            ])
            await channel_send(
                self.kanal,
                c_container(*duyuru_items, color=COLORS.GAME),
                content=self.ping or None,
            )
            await respond(interaction, c_action_card(
                "✅ Duyuru Gönderildi",
                fields=[
                    ("📌 Kanal", self.kanal.mention),
                    ("🔔 Ping", f"`{self.ping}`" if self.ping else "_Yok_"),
                    ("👤 Duyuran", interaction.user.mention),
                ],
                color=COLORS.SUCCESS,
            ), ephemeral=True)
        except discord.Forbidden:
            await respond(interaction,
                c_card("## ❌ Yetki Hatası", body=f"{self.kanal.mention} kanalına yazma iznim yok.", color=COLORS.DANGER),
                ephemeral=True,
            )
        except discord.HTTPException as ex:
            await respond(interaction,
                c_card("## ❌ Hata", body=f"```{ex}```", color=COLORS.DANGER),
                ephemeral=True,
            )
