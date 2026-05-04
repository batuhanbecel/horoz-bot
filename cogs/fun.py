import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime, timezone


SEKIZ_TOP_YANIT = [
    "Kesinlikle evet.", "Evet, şüphesiz.", "Bence evet.",
    "Muhtemelen evet.", "Olumlu görünüyor.", "Evet.",
    "İşaretler evet diyor.", "En iyi ihtimalle evet.",
    "Şu an cevap veremiyorum, tekrar sor.", "Daha sonra tekrar sor.",
    "Daha iyi söylemesem olur.", "Şu an tahmin edemiyorum.",
    "Bunun üzerine durmana gerek yok.", "Cevap bulanık.",
    "Hayır.", "Görünüşe göre hayır.", "Hayırla dön.",
    "Çok şüpheli.", "Pek sanmıyorum.", "Kesinlikle hayır.",
]


def fun_embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.timestamp = discord.utils.utcnow()
    return e


class PollView(discord.ui.View):
    def __init__(self, soru: str, seçenekler: list[str]):
        super().__init__(timeout=None)
        self.soru = soru
        self.seçenekler = seçenekler
        self.votes: dict[int, int] = {}
        self.counts = [0] * len(seçenekler)
        for i, opt in enumerate(seçenekler):
            self.add_item(PollButton(i, opt, self))

    def build_embed(self) -> discord.Embed:
        total = sum(self.counts)
        embed = discord.Embed(title=f"📊 {self.soru}", color=discord.Color.blurple())
        for i, opt in enumerate(self.seçenekler):
            pct = (self.counts[i] / total * 100) if total else 0
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            embed.add_field(
                name=f"{i + 1}. {opt}",
                value=f"`{bar}` {pct:.1f}% ({self.counts[i]} oy)",
                inline=False,
            )
        embed.set_footer(text=f"Toplam oy: {total}")
        return embed


class PollButton(discord.ui.Button):
    def __init__(self, index: int, label: str, poll: "PollView"):
        super().__init__(label=f"{index + 1}. {label}", style=discord.ButtonStyle.primary, row=index // 3)
        self.index = index
        self.poll = poll

    async def callback(self, interaction: discord.Interaction):
        uid = interaction.user.id
        prev = self.poll.votes.get(uid)
        if prev is not None:
            self.poll.counts[prev] -= 1
        self.poll.votes[uid] = self.index
        self.poll.counts[self.index] += 1
        await interaction.response.edit_message(embed=self.poll.build_embed(), view=self.poll)


class EventView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.attendees: set[int] = set()

    @discord.ui.button(label="✅ Katılıyorum", style=discord.ButtonStyle.success)
    async def katılıyorum(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id
        if uid in self.attendees:
            self.attendees.discard(uid)
            await interaction.response.send_message("Katılımınız iptal edildi.", ephemeral=True)
        else:
            self.attendees.add(uid)
            await interaction.response.send_message(
                f"Etkinliğe katılım kaydınız alındı! Toplam: **{len(self.attendees)}** kişi.", ephemeral=True
            )

    @discord.ui.button(label="👥 Katılımcılar", style=discord.ButtonStyle.secondary)
    async def katılımcılar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.attendees:
            await interaction.response.send_message("Henüz katılımcı yok.", ephemeral=True)
            return
        mentions = [f"<@{uid}>" for uid in self.attendees]
        await interaction.response.send_message(
            f"**Katılımcılar ({len(self.attendees)}):**\n" + ", ".join(mentions), ephemeral=True
        )


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /yazıtura
    @app_commands.command(name="yazıtura", description="Yazı mı tura mı? Bozuk para atar.")
    async def yazıtura(self, interaction: discord.Interaction):
        sonuç = random.choice(["Yazı", "Tura"])
        embed = fun_embed(f"🪙 {sonuç}!", f"{interaction.user.mention} parayı attı: **{sonuç}**", discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    # /zar
    @app_commands.command(name="zar", description="Zar atar.")
    @app_commands.describe(yüz="Zarın kaç yüzlü olduğu (varsayılan 6)", adet="Kaç zar atılsın (1-10)")
    async def zar(
        self,
        interaction: discord.Interaction,
        yüz: app_commands.Range[int, 2, 100] = 6,
        adet: app_commands.Range[int, 1, 10] = 1,
    ):
        sonuçlar = [random.randint(1, yüz) for _ in range(adet)]
        toplam = sum(sonuçlar)
        sonuç_str = " + ".join(f"**{s}**" for s in sonuçlar)
        embed = fun_embed(
            "🎲 Zar Atıldı!",
            f"{adet}d{yüz}: {sonuç_str}\n**Toplam: {toplam}**",
            discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    # /8top
    @app_commands.command(name="8top", description="Sihirli 8-top'a bir soru sor.")
    @app_commands.describe(soru="Sormak istediğin soru")
    async def sekiz_top(self, interaction: discord.Interaction, soru: str):
        yanıt = random.choice(SEKIZ_TOP_YANIT)
        embed = fun_embed(
            "🎱 Sihirli 8-Top",
            f"**Soru:** {soru}\n\n**Cevap:** {yanıt}",
            discord.Color.dark_blue(),
        )
        await interaction.response.send_message(embed=embed)

    # /anket
    @app_commands.command(name="anket", description="Butonlu anket oluşturur.")
    @app_commands.describe(
        soru="Anket sorusu",
        seçenek1="1. seçenek",
        seçenek2="2. seçenek",
        seçenek3="3. seçenek (isteğe bağlı)",
        seçenek4="4. seçenek (isteğe bağlı)",
        seçenek5="5. seçenek (isteğe bağlı)",
    )
    async def anket(
        self,
        interaction: discord.Interaction,
        soru: str,
        seçenek1: str,
        seçenek2: str,
        seçenek3: str | None = None,
        seçenek4: str | None = None,
        seçenek5: str | None = None,
    ):
        seçenekler = [s for s in [seçenek1, seçenek2, seçenek3, seçenek4, seçenek5] if s]
        view = PollView(soru, seçenekler)
        embed = view.build_embed()
        embed.set_footer(text=f"Anketi oluşturan: {interaction.user.display_name} | Toplam oy: 0")
        await interaction.response.send_message(embed=embed, view=view)

    # /etkinlik
    @app_commands.command(name="etkinlik", description="Sunucuda bir etkinlik duyurusu oluşturur.")
    @app_commands.describe(
        başlık="Etkinlik başlığı",
        açıklama="Etkinlik açıklaması",
        tarih="Tarih (örn: 25 Mayıs 2025)",
        saat="Saat (örn: 20:00)",
        ses_kanalı="Etkinliğin gerçekleşeceği ses kanalı (sunucudan seç)",
        konum="Yazılı konum / adres (ses kanalı seçilmezse)",
        resim="Etkinlik görseli (dosya yükle)",
    )
    @app_commands.checks.has_permissions(manage_events=True)
    async def etkinlik(
        self,
        interaction: discord.Interaction,
        başlık: str,
        açıklama: str,
        tarih: str,
        saat: str,
        ses_kanalı: discord.VoiceChannel | None = None,
        konum: str | None = None,
        resim: discord.Attachment | None = None,
    ):
        embed = discord.Embed(
            title=f"📅 {başlık}",
            description=açıklama,
            color=discord.Color.purple(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="📆 Tarih", value=tarih, inline=True)
        embed.add_field(name="🕐 Saat", value=saat, inline=True)

        if ses_kanalı:
            embed.add_field(name="🔊 Ses Kanalı", value=ses_kanalı.mention, inline=True)
        elif konum:
            embed.add_field(name="📍 Konum", value=konum, inline=True)

        if resim:
            if resim.content_type and resim.content_type.startswith("image/"):
                embed.set_image(url=resim.url)
            else:
                await interaction.response.send_message(
                    embed=fun_embed("Hata", "Yüklenen dosya bir resim olmalıdır.", discord.Color.red()),
                    ephemeral=True,
                )
                return

        embed.set_footer(
            text=f"Oluşturan: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        view = EventView()
        await interaction.response.send_message(embed=embed, view=view)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz.", ephemeral=True
            )
        else:
            await interaction.response.send_message(str(error), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
