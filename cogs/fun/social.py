import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from ._shared import parse_datetime
from .._v2 import (
    COLORS, c_text, c_section, c_thumbnail, c_separator, c_media, c_container,
    c_card, c_progress, respond, update, followup as v2_followup, channel_send, error_response,
)


# ── Anket ─────────────────────────────────────────────────────────────────────

# Lider olan seçenek için hafif vurgu emoji'si
_RANK_EMOJI = ["🥇", "🥈", "🥉"]


class PollView(discord.ui.View):
    def __init__(self, soru: str, seçenekler: list[str], creator: discord.Member | None = None):
        super().__init__(timeout=None)
        self.soru = soru
        self.seçenekler = seçenekler
        self.creator = creator
        self.votes: dict[int, int] = {}
        self.counts = [0] * len(seçenekler)
        for i, opt in enumerate(seçenekler):
            self.add_item(PollButton(i, opt, self))

    def build_card(self) -> tuple[dict, ...]:
        total = sum(self.counts)
        # Lider sıralaması (oy sayısına göre)
        ranking = sorted(range(len(self.seçenekler)), key=lambda i: -self.counts[i])
        rank_map = {idx: pos for pos, idx in enumerate(ranking)}

        items: list[dict] = [c_text(f"## 📊 {self.soru}")]

        for i, opt in enumerate(self.seçenekler):
            pct = (self.counts[i] / total * 100) if total else 0
            bar = c_progress(self.counts[i], max(total, 1), length=14)
            rank_emoji = _RANK_EMOJI[rank_map[i]] if total > 0 and self.counts[i] > 0 and rank_map[i] < 3 else f"`#{i + 1}`"
            items.append(c_separator())
            items.append(c_text(
                f"{rank_emoji} **{opt}**\n"
                f"`{bar}` `{pct:5.1f}%` · **{self.counts[i]}** oy"
            ))

        items.append(c_separator())
        creator_str = f" · 👤 {self.creator.mention}" if self.creator else ""
        items.append(c_text(f"-# 🗳️ Toplam: **{total}** oy{creator_str}"))

        return (c_container(*items, color=COLORS.PRIMARY),)


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
        await update(interaction, *self.poll.build_card(), view=self.poll)


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
        thumb = str(interaction.client.user.display_avatar.url)

        start_time = parse_datetime(self.tarih.value, self.baslangic.value)
        if start_time is None:
            return await v2_followup(interaction,
                c_card(
                    "## ❌ Geçersiz Tarih/Saat",
                    body="Desteklenen formatlar:\n• `25.05.2026`  `20:00` veya `20.00`\n• `25 Mayıs 2026`  `20:00`",
                    thumbnail=thumb,
                    color=0xED4245,
                ),
                ephemeral=True,
            )

        if start_time <= discord.utils.utcnow():
            return await v2_followup(interaction,
                c_card("## ❌ Hata", body="Başlangıç zamanı geçmişte olamaz.", thumbnail=thumb, color=0xED4245),
                ephemeral=True,
            )

        end_time = None
        if self.bitis.value.strip():
            end_time = parse_datetime(self.tarih.value, self.bitis.value)
            if end_time is None:
                return await v2_followup(interaction,
                    c_card("## ❌ Hata", body="Bitiş saati formatı tanınamadı.", thumbnail=thumb, color=0xED4245),
                    ephemeral=True,
                )

        if self.e_kanal is None and end_time is None:
            end_time = start_time + timedelta(hours=1)

        image_bytes: bytes | None = None
        if self.e_resim:
            if not (self.e_resim.content_type and self.e_resim.content_type.startswith("image/")):
                return await v2_followup(interaction,
                    c_card("## ❌ Hata", body="Yüklenen dosya bir resim olmalıdır.", thumbnail=thumb, color=0xED4245),
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
            return await v2_followup(interaction,
                c_card("## ❌ Hata", body=f"Etkinlik oluşturulamadı: {exc}", thumbnail=thumb, color=0xED4245),
                ephemeral=True,
            )

        event_url = f"https://discord.com/events/{interaction.guild.id}/{ev.id}"

        body_lines = [
            self.açıklama.value,
            "",
            f"📆 **Başlangıç:** <t:{int(start_time.timestamp())}:F>",
        ]
        if end_time:
            body_lines.append(f"🏁 **Bitiş:** <t:{int(end_time.timestamp())}:t>")
        if self.e_kanal:
            body_lines.append(f"🔊 **Kanal:** {self.e_kanal.mention}")
        elif self.konum.value:
            body_lines.append(f"📍 **Konum:** {self.konum.value}")
        body_lines.append(f"🔗 **Bağlantı:** [Discord'da Aç]({event_url})")
        body_lines.append(f"\n-# Oluşturan: {interaction.user.display_name}")

        items: list[dict] = [
            c_section(c_text(f"## ✅ Etkinlik Oluşturuldu"), accessory=c_thumbnail(thumb)),
            c_separator(),
            c_text("\n".join(body_lines)),
        ]
        if self.e_resim:
            items.append(c_separator())
            items.append(c_media(self.e_resim.url))

        await v2_followup(interaction, c_container(*items, color=0x57F287), ephemeral=True)

        if self.e_duyuru:
            duyuru_lines = [
                self.açıklama.value,
                "",
                f"📆 **Başlangıç:** <t:{int(start_time.timestamp())}:F>",
            ]
            if self.e_kanal:
                duyuru_lines.append(f"🔊 **Kanal:** {self.e_kanal.mention}")
            elif self.konum.value:
                duyuru_lines.append(f"📍 **Konum:** {self.konum.value}")
            duyuru_lines.append(f"\n[**→ Etkinliğe Git**]({event_url})")
            duyuru_lines.append(f"\n-# Oluşturan: {interaction.user.display_name}")

            duyuru_items: list[dict] = [
                c_section(c_text(f"## 📣 Yeni Etkinlik: {self.e_başlık}"), accessory=c_thumbnail(thumb)),
                c_separator(),
                c_text("\n".join(duyuru_lines)),
            ]
            if self.e_resim:
                duyuru_items.append(c_separator())
                duyuru_items.append(c_media(self.e_resim.url))

            try:
                await channel_send(self.e_duyuru, c_container(*duyuru_items, color=0x9B59B6))
            except discord.Forbidden:
                pass

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await error_response(interaction, str(error))


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
        view = PollView(soru, seçenekler, creator=interaction.user)
        await respond(interaction, *view.build_card(), view=view)

    # /etkinlik
    @app_commands.command(name="etkinlik", description="Discord sunucu etkinliği oluşturur.")
    @app_commands.describe(
        başlık="Etkinlik başlığı",
        kanal="Etkinliğin gerçekleşeceği ses kanalı (isteğe bağlı)",
        duyuru_yap="Etkinlik bağlantısının duyurulacağı metin kanalı",
        resim="Etkinlik kapak görseli (dosya yükle)",
    )
    @app_commands.guild_only()
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

    @app_commands.command(name="anket-hızlı", description="Discord'un yerel anket sistemiyle hızlı oylama.")
    @app_commands.describe(
        soru="Anket sorusu",
        seçenek1="1. seçenek",
        seçenek2="2. seçenek",
        seçenek3="3. seçenek (isteğe bağlı)",
        seçenek4="4. seçenek (isteğe bağlı)",
        seçenek5="5. seçenek (isteğe bağlı)",
    )
    @app_commands.choices(süre=[
        app_commands.Choice(name="1 saat", value=1),
        app_commands.Choice(name="4 saat", value=4),
        app_commands.Choice(name="8 saat", value=8),
        app_commands.Choice(name="24 saat", value=24),
        app_commands.Choice(name="3 gün", value=72),
        app_commands.Choice(name="7 gün", value=168),
    ])
    async def anket_hizli(
        self,
        interaction: discord.Interaction,
        soru: str,
        seçenek1: str,
        seçenek2: str,
        seçenek3: str | None = None,
        seçenek4: str | None = None,
        seçenek5: str | None = None,
        süre: int = 24,
    ):
        poll = discord.Poll(question=soru, duration=timedelta(hours=süre))
        for s in [seçenek1, seçenek2, seçenek3, seçenek4, seçenek5]:
            if s:
                poll.add_answer(text=s)
        await interaction.response.send_message(poll=poll)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Bu komutu kullanmak için gerekli yetkiye sahip değilsiniz." \
            if isinstance(error, app_commands.MissingPermissions) else str(error)
        await error_response(interaction, msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(Social(bot))
