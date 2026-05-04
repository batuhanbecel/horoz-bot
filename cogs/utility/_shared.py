import discord

RENK_MAP: dict[str, discord.Color] = {
    "mavi":    discord.Color.blue(),
    "yesil":   discord.Color.green(),
    "kirmizi": discord.Color.red(),
    "altin":   discord.Color.gold(),
    "mor":     discord.Color.purple(),
    "turuncu": discord.Color.orange(),
    "pembe":   discord.Color.magenta(),
}


def _emb(title: str, desc: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text="Horoz Bot")
    e.timestamp = discord.utils.utcnow()
    return e


class MesajModal(discord.ui.Modal, title="Mesaj Gönder"):
    içerik = discord.ui.TextInput(
        label="Mesaj İçeriği",
        style=discord.TextStyle.paragraph,
        placeholder="Göndermek istediğin mesajı buraya yaz...",
        max_length=2000,
    )

    def __init__(self, kanal: discord.TextChannel):
        super().__init__()
        self.kanal = kanal

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.kanal.send(self.içerik.value)
            await interaction.response.send_message(
                embed=_emb("✅ Mesaj Gönderildi", f"{self.kanal.mention} kanalına mesaj gönderildi.", discord.Color.green()),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=_emb("❌ Hata", f"{self.kanal.mention} kanalına yazma iznim yok.", discord.Color.red()),
                ephemeral=True,
            )


class EmbedModal(discord.ui.Modal, title="Embed Mesaj Gönder"):
    başlık_f = discord.ui.TextInput(label="Başlık", placeholder="Embed başlığı", max_length=256)
    içerik_f = discord.ui.TextInput(
        label="İçerik",
        style=discord.TextStyle.paragraph,
        placeholder="Embed metni...",
        max_length=4000,
    )

    def __init__(self, kanal: discord.TextChannel, renk: discord.Color):
        super().__init__()
        self.kanal = kanal
        self.renk  = renk

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=self.başlık_f.value, description=self.içerik_f.value, color=self.renk)
        embed.set_footer(text=f"Gönderen: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        try:
            await self.kanal.send(embed=embed)
            await interaction.response.send_message(
                embed=_emb("✅ Embed Gönderildi", f"{self.kanal.mention} kanalına embed gönderildi.", discord.Color.green()),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=_emb("❌ Hata", f"{self.kanal.mention} kanalına yazma iznim yok.", discord.Color.red()),
                ephemeral=True,
            )


class DuyuruModal(discord.ui.Modal, title="Duyuru Gönder"):
    içerik_f = discord.ui.TextInput(
        label="Duyuru İçeriği",
        style=discord.TextStyle.paragraph,
        placeholder="Duyuru metni...",
        max_length=2000,
    )

    def __init__(self, kanal: discord.TextChannel, ping: str):
        super().__init__()
        self.kanal = kanal
        self.ping  = ping

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📣 Duyuru", description=self.içerik_f.value, color=discord.Color.gold())
        embed.set_footer(text=f"Duyuran: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        try:
            await self.kanal.send(content=self.ping or None, embed=embed)
            await interaction.response.send_message(
                embed=_emb("✅ Duyuru Gönderildi", f"{self.kanal.mention} kanalına duyuru gönderildi.", discord.Color.green()),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=_emb("❌ Hata", f"{self.kanal.mention} kanalına yazma iznim yok.", discord.Color.red()),
                ephemeral=True,
            )
