import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime, timezone, timedelta


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

TÜRKÇE_AYLAR = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}


def fun_embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.timestamp = discord.utils.utcnow()
    return e


def normalize_saat(saat: str) -> str:
    """'20.00' → '20:00', '2000' → '20:00', '20:00' → '20:00'"""
    saat = saat.strip()
    if "." in saat and ":" not in saat:          # 20.00 formatı
        return saat.replace(".", ":")
    if saat.isdigit() and len(saat) == 4:         # 2000 formatı
        return f"{saat[:2]}:{saat[2:]}"
    return saat


def parse_datetime(tarih: str, saat: str) -> datetime | None:
    """'25 Mayıs 2026' veya '25.05.2026' + '20:00' → UTC datetime"""
    tarih = tarih.strip()
    saat = normalize_saat(saat.strip())

    for fmt in ("%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(f"{tarih} {saat}", fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    parts = tarih.split()
    if len(parts) == 3:
        gun, ay_str, yil = parts
        ay = TÜRKÇE_AYLAR.get(ay_str.lower())
        if ay:
            try:
                h, m = (int(x) for x in (saat.split(":") + ["0"])[:2])
                return datetime(int(yil), ay, int(gun), h, m, tzinfo=timezone.utc)
            except (ValueError, IndexError):
                pass

    return None


# ── Anket ─────────────────────────────────────────────────────────────────────

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


# ── Etkinlik Modal ─────────────────────────────────────────────────────────────

class EtkinlikModal(discord.ui.Modal, title="Etkinlik Detayları"):
    açıklama = discord.ui.TextInput(
        label="Açıklama",
        style=discord.TextStyle.paragraph,
        placeholder="Etkinlik hakkında detaylar...",
        max_length=1000,
    )
    tarih = discord.ui.TextInput(
        label="Tarih",
        placeholder="25.05.2026  veya  25 Mayıs 2026",
        max_length=25,
    )
    baslangic = discord.ui.TextInput(
        label="Başlangıç Saati (UTC)",
        placeholder="20:00  veya  20.00",
        max_length=8,
    )
    bitis = discord.ui.TextInput(
        label="Bitiş Saati — isteğe bağlı",
        placeholder="22:00  (boş bırakılırsa +1 saat otomatik)",
        required=False,
        max_length=8,
    )
    konum = discord.ui.TextInput(
        label="Yazılı Konum — isteğe bağlı",
        placeholder="Ses kanalı seçilmediyse konum giriniz",
        required=False,
        max_length=100,
    )

    def __init__(
        self,
        başlık: str,
        kanal: discord.VoiceChannel | None,
        duyuru_yap: discord.TextChannel | None,
        resim: discord.Attachment | None,
    ):
        super().__init__()
        self.e_başlık = başlık
        self.e_kanal = kanal
        self.e_duyuru = duyuru_yap
        self.e_resim = resim

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        start_time = parse_datetime(self.tarih.value, self.baslangic.value)
        if start_time is None:
            return await interaction.followup.send(
                embed=fun_embed(
                    "Hata",
                    "Tarih/saat formatı tanınamadı.\n"
                    "Desteklenen formatlar:\n"
                    "• `25.05.2026`  `20:00` veya `20.00`\n"
                    "• `25 Mayıs 2026`  `20:00`",
                    discord.Color.red(),
                ),
                ephemeral=True,
            )

        if start_time <= discord.utils.utcnow():
            return await interaction.followup.send(
                embed=fun_embed("Hata", "Başlangıç zamanı geçmişte olamaz.", discord.Color.red()),
                ephemeral=True,
            )

        end_time = None
        if self.bitis.value.strip():
            end_time = parse_datetime(self.tarih.value, self.bitis.value)
            if end_time is None:
                return await interaction.followup.send(
                    embed=fun_embed("Hata", "Bitiş saati formatı tanınamadı.", discord.Color.red()),
                    ephemeral=True,
                )

        if self.e_kanal is None and end_time is None:
            end_time = start_time + timedelta(hours=1)

        image_bytes: bytes | None = None
        if self.e_resim:
            if not (self.e_resim.content_type and self.e_resim.content_type.startswith("image/")):
                return await interaction.followup.send(
                    embed=fun_embed("Hata", "Yüklenen dosya bir resim olmalıdır.", discord.Color.red()),
                    ephemeral=True,
                )
            image_bytes = await self.e_resim.read()

        event_kwargs: dict = dict(
            name=self.e_başlık,
            description=self.açıklama.value,
            start_time=start_time,
            privacy_level=discord.PrivacyLevel.guild_only,
        )

        if self.e_kanal:
            event_kwargs["entity_type"] = discord.EntityType.voice
            event_kwargs["channel"] = self.e_kanal
            if end_time:
                event_kwargs["end_time"] = end_time
        else:
            event_kwargs["entity_type"] = discord.EntityType.external
            event_kwargs["location"] = self.konum.value or "Belirtilmedi"
            event_kwargs["end_time"] = end_time

        if image_bytes:
            event_kwargs["image"] = image_bytes

        try:
            ev = await interaction.guild.create_scheduled_event(**event_kwargs)
        except discord.HTTPException as exc:
            return await interaction.followup.send(
                embed=fun_embed("Hata", f"Etkinlik oluşturulamadı: {exc}", discord.Color.red()),
                ephemeral=True,
            )

        event_url = f"https://discord.com/events/{interaction.guild.id}/{ev.id}"

        embed = discord.Embed(
            title=f"📅 {self.e_başlık}",
            description=self.açıklama.value,
            color=discord.Color.purple(),
            url=event_url,
            timestamp=start_time,
        )
        embed.add_field(name="📆 Başlangıç", value=f"<t:{int(start_time.timestamp())}:F>", inline=True)
        if end_time:
            embed.add_field(name="🏁 Bitiş", value=f"<t:{int(end_time.timestamp())}:t>", inline=True)
        if self.e_kanal:
            embed.add_field(name="🔊 Kanal", value=self.e_kanal.mention, inline=True)
        elif self.konum.value:
            embed.add_field(name="📍 Konum", value=self.konum.value, inline=True)
        embed.add_field(name="🔗 Bağlantı", value=f"[Discord'da Aç]({event_url})", inline=False)
        if self.e_resim:
            embed.set_image(url=self.e_resim.url)
        embed.set_footer(
            text=f"Oluşturan: {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

        if self.e_duyuru:
            duyuru = discord.Embed(
                title=f"📣 Yeni Etkinlik: {self.e_başlık}",
                description=f"{self.açıklama.value}\n\n[**→ Etkinliğe Git**]({event_url})",
                color=discord.Color.purple(),
                url=event_url,
                timestamp=start_time,
            )
            duyuru.add_field(name="📆 Başlangıç", value=f"<t:{int(start_time.timestamp())}:F>", inline=True)
            if self.e_kanal:
                duyuru.add_field(name="🔊 Kanal", value=self.e_kanal.mention, inline=True)
            elif self.konum.value:
                duyuru.add_field(name="📍 Konum", value=self.konum.value, inline=True)
            if self.e_resim:
                duyuru.set_image(url=self.e_resim.url)
            duyuru.set_footer(
                text=f"Oluşturan: {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url,
            )
            try:
                await self.e_duyuru.send(embed=duyuru)
            except discord.Forbidden:
                pass

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        msg = str(error)
        if interaction.response.is_done():
            await interaction.followup.send(embed=fun_embed("Hata", msg, discord.Color.red()), ephemeral=True)
        else:
            await interaction.response.send_message(embed=fun_embed("Hata", msg, discord.Color.red()), ephemeral=True)


# ── Fun Cog ───────────────────────────────────────────────────────────────────

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

    # /etkinlik — modal ile Discord Scheduled Event oluşturur
    @app_commands.command(name="etkinlik", description="Discord sunucu etkinliği oluşturur.")
    @app_commands.describe(
        başlık="Etkinlik başlığı",
        kanal="Etkinliğin gerçekleşeceği ses kanalı (isteğe bağlı)",
        duyuru_yap="Etkinlik bağlantısının duyurulacağı metin kanalı",
        resim="Etkinlik kapak görseli (dosya yükle)",
    )
    @app_commands.checks.has_permissions(manage_events=True)
    async def etkinlik(
        self,
        interaction: discord.Interaction,
        başlık: str,
        kanal: discord.VoiceChannel | None = None,
        duyuru_yap: discord.TextChannel | None = None,
        resim: discord.Attachment | None = None,
    ):
        await interaction.response.send_modal(EtkinlikModal(başlık, kanal, duyuru_yap, resim))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz." \
            if isinstance(error, app_commands.MissingPermissions) else str(error)
        if interaction.response.is_done():
            await interaction.followup.send(embed=fun_embed("Hata", msg, discord.Color.red()), ephemeral=True)
        else:
            await interaction.response.send_message(embed=fun_embed("Hata", msg, discord.Color.red()), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
