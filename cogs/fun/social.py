import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from ._shared import fun_embed, parse_datetime


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


# ── Social Cog ────────────────────────────────────────────────────────────────

class Social(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
    await bot.add_cog(Social(bot))
