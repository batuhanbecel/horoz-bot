from __future__ import annotations
from typing import TYPE_CHECKING
import discord
import random
from collections import deque
from ._shared import GuildPlayer, Track, now_playing_card, stopped_card, duration_fmt, yt_thumbnail
from .._v2 import (
    COLORS, msg_edit, c_text, c_section, c_thumbnail, c_separator, c_container,
    c_card, c_action_card, respond as v2_respond, followup as v2_followup,
)

if TYPE_CHECKING:
    from .player import Music


def _ephemeral_status(emoji: str, title: str, body: str = "", color: int = COLORS.PRIMARY) -> dict:
    return c_card(f"## {emoji} {title}", body=body, color=color)


class PlayerView(discord.ui.View):
    def __init__(self, cog: "Music", guild_id: int):
        super().__init__(timeout=7200)
        self.cog = cog
        self.guild_id = guild_id

    def vc(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        return interaction.guild.voice_client

    def player(self) -> GuildPlayer:
        return self.cog.get_player(self.guild_id)

    def _bot_thumb(self, interaction: discord.Interaction) -> str:
        return str(interaction.client.user.display_avatar.url)

    # Satır 0 ──────────────────────────────────────────────────────────────────

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def yeniden(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc(interaction)
        p = self.player()
        if not vc or not p.current:
            return await v2_respond(interaction,
                _ephemeral_status("⚠️", "Çalan Yok", "Şu an çalan bir şey yok.", COLORS.WARNING),
                ephemeral=True,
            )
        track = p.current
        track.stream_url = None
        p.force_next = True
        p.queue.appendleft(track)
        p.current = None
        vc.stop()
        await interaction.response.defer()

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, row=0)
    async def duraklat(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc(interaction)
        if not vc:
            return await v2_respond(interaction,
                _ephemeral_status("❌", "Hata", "Bot ses kanalında değil.", COLORS.DANGER),
                ephemeral=True,
            )
        if vc.is_playing():
            vc.pause()
            await v2_respond(interaction,
                _ephemeral_status("⏸️", "Duraklatıldı", "Müzik duraklatıldı.", COLORS.WARNING),
                ephemeral=True,
            )
        elif vc.is_paused():
            vc.resume()
            await v2_respond(interaction,
                _ephemeral_status("▶️", "Devam Ediyor", "Müzik devam ediyor.", COLORS.SUCCESS),
                ephemeral=True,
            )
        else:
            await v2_respond(interaction,
                _ephemeral_status("⚠️", "Çalan Yok", "Şu an çalan bir şey yok.", COLORS.WARNING),
                ephemeral=True,
            )

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def atla(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc(interaction)
        p = self.player()
        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await v2_respond(interaction,
                _ephemeral_status("⚠️", "Çalan Yok", "Şu an çalan bir şey yok.", COLORS.WARNING),
                ephemeral=True,
            )
        p.force_next = True
        vc.stop()
        await interaction.response.defer()

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def durdur(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc(interaction)
        p = self.player()
        if not vc:
            return await v2_respond(interaction,
                _ephemeral_status("❌", "Hata", "Bot ses kanalında değil.", COLORS.DANGER),
                ephemeral=True,
            )
        p.queue.clear()
        p.current = None
        p.loop = False
        p.force_next = False
        try:
            await msg_edit(interaction.message, stopped_card())
        except Exception:
            pass
        p.player_message = None
        await vc.disconnect()
        await interaction.response.defer()

    # Satır 1 ──────────────────────────────────────────────────────────────────

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, row=1)
    async def ses_azalt(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc(interaction)
        p = self.player()
        p.volume = max(0.0, round(p.volume - 0.1, 1))
        if vc and vc.source:
            vc.source.volume = p.volume
        await v2_respond(interaction,
            _ephemeral_status("🔉", "Ses Azaltıldı", f"Yeni seviye: **`{int(p.volume * 100)}%`**", COLORS.MUSIC),
            ephemeral=True,
        )

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=1)
    async def ses_artir(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc(interaction)
        p = self.player()
        p.volume = min(2.0, round(p.volume + 0.1, 1))
        if vc and vc.source:
            vc.source.volume = p.volume
        await v2_respond(interaction,
            _ephemeral_status("🔊", "Ses Artırıldı", f"Yeni seviye: **`{int(p.volume * 100)}%`**", COLORS.MUSIC),
            ephemeral=True,
        )

    @discord.ui.button(emoji="🔁", label="Döngü", style=discord.ButtonStyle.secondary, row=1)
    async def dongu(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = self.player()
        p.loop = not p.loop
        durum = "Açık 🔂" if p.loop else "Kapalı"
        body = "Şu an çalan şarkı sürekli tekrar edecek." if p.loop else "Döngü kapatıldı."
        await v2_respond(interaction,
            _ephemeral_status("🔁", f"Döngü {durum}", body, COLORS.MUSIC),
            ephemeral=True,
        )

    @discord.ui.button(emoji="🔀", label="Karıştır", style=discord.ButtonStyle.secondary, row=1)
    async def karistir(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = self.player()
        if len(p.queue) < 2:
            return await v2_respond(interaction,
                _ephemeral_status("⚠️", "Yeterli Şarkı Yok", "Karıştırmak için en az **2 şarkı** gerekli.", COLORS.WARNING),
                ephemeral=True,
            )
        q = list(p.queue)
        random.shuffle(q)
        p.queue = deque(q)
        await v2_respond(interaction,
            _ephemeral_status("🔀", "Karıştırıldı", f"`{len(q)}` şarkı rastgele sıralandı.", COLORS.SUCCESS),
            ephemeral=True,
        )

    @discord.ui.button(emoji="📋", label="Sıra", style=discord.ButtonStyle.secondary, row=1)
    async def sira(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = self.player()
        if not p.current and not p.queue:
            return await v2_respond(interaction,
                _ephemeral_status("📋", "Sıra Boş", "Sıra boş — `/müzik çal` ile şarkı ekleyin.", COLORS.WARNING),
                ephemeral=True,
            )

        sections: list[dict] = [c_text("## 📋 Müzik Sırası")]
        if p.current:
            sections.append(c_separator())
            sections.append(c_text(
                f"▶️ **Şu An**\n┗ [{p.current.title}]({p.current.webpage_url}) · `{duration_fmt(p.current.duration)}`"
            ))
        if p.queue:
            queue_lines = []
            for i, t in enumerate(list(p.queue)[:10], 1):
                queue_lines.append(f"`#{i:02d}` [{t.title[:60]}]({t.webpage_url}) · `{duration_fmt(t.duration)}`")
            sections.append(c_separator())
            sections.append(c_text("\n".join(queue_lines)))
            if len(p.queue) > 10:
                sections.append(c_separator())
                sections.append(c_text(f"-# ve `{len(p.queue) - 10}` şarkı daha..."))

        await v2_respond(interaction, c_container(*sections, color=COLORS.MUSIC), ephemeral=True)


class SearchButton(discord.ui.Button):
    def __init__(self, index: int, entry: dict, user: discord.Member, cog: "Music"):
        super().__init__(label=str(index), style=discord.ButtonStyle.primary)
        self.entry = entry
        self.user = user
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            return await v2_respond(interaction,
                _ephemeral_status("🚫", "Erişim Engellendi", "Bu seçim size ait değil.", COLORS.DANGER),
                ephemeral=True,
            )

        vc = await self.cog.ensure_voice(interaction)
        if not vc:
            return

        vid_id = self.entry.get("id", "")
        url = self.entry.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None)
        if not url:
            return await v2_respond(interaction,
                _ephemeral_status("❌", "URL Çözülemedi", "Bu sonuç için URL alınamadı.", COLORS.DANGER),
                ephemeral=True,
            )

        await interaction.response.defer()
        player = self.cog.get_player(interaction.guild_id)
        player.text_channel_id = interaction.channel_id
        track = Track(
            title=self.entry.get("title", "Bilinmiyor"),
            webpage_url=url,
            requester=interaction.user,
            duration=self.entry.get("duration", 0),
            stream_url=None,
        )

        track_thumb = yt_thumbnail(url) or str(interaction.user.display_avatar.url)

        if vc.is_playing() or vc.is_paused():
            player.queue.append(track)
            await v2_followup(interaction, c_container(
                c_section(
                    c_text(f"## 📋 Sıraya Eklendi\n### [{track.title}]({track.webpage_url})"),
                    accessory=c_thumbnail(track_thumb),
                ),
                c_separator(),
                c_text(f"⏱️ `{duration_fmt(track.duration)}` · 👤 {interaction.user.mention} · 📋 `#{len(player.queue)}`"),
                color=COLORS.MUSIC,
            ), ephemeral=True)
        else:
            player.queue.appendleft(track)
            await self.cog._play_next(interaction.guild_id, vc)
            await v2_followup(interaction, c_container(
                c_section(
                    c_text(f"## ✅ Çalmaya Başlıyor\n### [{track.title}]({track.webpage_url})"),
                    accessory=c_thumbnail(track_thumb),
                ),
                c_separator(),
                c_text(f"⏱️ `{duration_fmt(track.duration)}` · 👤 {interaction.user.mention}"),
                color=COLORS.SUCCESS,
            ), ephemeral=True)
        self.view.stop()


class SearchView(discord.ui.View):
    def __init__(self, entries: list, user: discord.Member, cog: "Music"):
        super().__init__(timeout=30)
        self.entries = entries
        self.user = user
        self.cog = cog
        for i, entry in enumerate(entries):
            self.add_item(SearchButton(i + 1, entry, user, cog))
