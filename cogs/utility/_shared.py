import discord
from .._v2 import c_card, c_text, c_container, respond, channel_send

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
        thumb = str(interaction.client.user.display_avatar.url)
        try:
            await self.kanal.send(self.içerik.value)
            await respond(interaction,
                c_card("## ✅ Mesaj Gönderildi", body=f"{self.kanal.mention} kanalına mesaj gönderildi.", thumbnail=thumb, color=0x57F287),
                ephemeral=True,
            )
        except discord.Forbidden:
            await respond(interaction,
                c_card("## ❌ Hata", body=f"{self.kanal.mention} kanalına yazma iznim yok.", thumbnail=thumb, color=0xED4245),
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
        thumb = str(interaction.client.user.display_avatar.url)
        lines = [
            f"**{self.başlık_f.value}**",
            "",
            self.içerik_f.value,
            "",
            f"-# Gönderen: {interaction.user.display_name}",
        ]
        try:
            await channel_send(self.kanal, c_container(c_text("\n".join(lines)), color=self.renk))
            await respond(interaction,
                c_card("## ✅ Embed Gönderildi", body=f"{self.kanal.mention} kanalına embed gönderildi.", thumbnail=thumb, color=0x57F287),
                ephemeral=True,
            )
        except discord.Forbidden:
            await respond(interaction,
                c_card("## ❌ Hata", body=f"{self.kanal.mention} kanalına yazma iznim yok.", thumbnail=thumb, color=0xED4245),
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
        thumb = str(interaction.client.user.display_avatar.url)
        lines = [
            "**📣 Duyuru**",
            "",
            self.içerik_f.value,
            "",
            f"-# Duyuran: {interaction.user.display_name}",
        ]
        try:
            await channel_send(
                self.kanal,
                c_container(c_text("\n".join(lines)), color=0xF1C40F),
                content=self.ping or None,
            )
            await respond(interaction,
                c_card("## ✅ Duyuru Gönderildi", body=f"{self.kanal.mention} kanalına duyuru gönderildi.", thumbnail=thumb, color=0x57F287),
                ephemeral=True,
            )
        except discord.Forbidden:
            await respond(interaction,
                c_card("## ❌ Hata", body=f"{self.kanal.mention} kanalına yazma iznim yok.", thumbnail=thumb, color=0xED4245),
                ephemeral=True,
            )
