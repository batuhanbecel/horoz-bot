import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from ._shared import parse_datetime
from .._v2 import (
    COLORS, c_text, c_section, c_thumbnail, c_separator, c_media, c_container,
    c_card, followup as v2_followup, channel_send, error_response,
)


# ── Etkinlik Modal

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
                ),
                ephemeral=True,
            )

        if start_time <= discord.utils.utcnow():
            return await v2_followup(interaction,
                c_card("## ❌ Hata", body="Başlangıç zamanı geçmişte olamaz.", thumbnail=thumb),
                ephemeral=True,
            )

        end_time = None
        if self.bitis.value.strip():
            end_time = parse_datetime(self.tarih.value, self.bitis.value)
            if end_time is None:
                return await v2_followup(interaction,
                    c_card("## ❌ Hata", body="Bitiş saati formatı tanınamadı.", thumbnail=thumb),
                    ephemeral=True,
                )

        if self.e_kanal is None and end_time is None:
            end_time = start_time + timedelta(hours=1)

        image_bytes: bytes | None = None
        if self.e_resim:
            if not (self.e_resim.content_type and self.e_resim.content_type.startswith("image/")):
                return await v2_followup(interaction,
                    c_card("## ❌ Hata", body="Yüklenen dosya bir resim olmalıdır.", thumbnail=thumb),
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
                c_card("## ❌ Hata", body=f"Etkinlik oluşturulamadı: {exc}", thumbnail=thumb),
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

        await v2_followup(interaction, c_container(*items), ephemeral=True)

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
                await channel_send(self.e_duyuru, c_container(*duyuru_items))
            except discord.Forbidden:
                pass

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await error_response(interaction, str(error))


# ── Social Cog ────────────────────────────────────────────────────────────────

class Social(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

    @app_commands.command(name="anket", description="Discord'un yerel anket sistemiyle oylama.")
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
    async def anket(
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
