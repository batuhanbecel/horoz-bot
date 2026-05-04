from __future__ import annotations
from typing import TYPE_CHECKING
import discord
import random
from ._shared import GuildPlayer, Track, now_playing_embed, stopped_embed, duration_fmt, music_embed

if TYPE_CHECKING:
    from .player import Music


class PlayerView(discord.ui.View):
    def __init__(self, cog: "Music", guild_id: int):
        super().__init__(timeout=7200)
        self.cog = cog
        self.guild_id = guild_id

    def vc(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        return interaction.guild.voice_client

    def player(self) -> GuildPlayer:
        return self.cog.get_player(self.guild_id)

    # Satır 0 ──────────────────────────────────────────────────────────────────

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=0)
    async def yeniden(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc(interaction)
        p = self.player()
        if not vc or not p.current:
            return await interaction.response.send_message("Şu an çalan bir şey yok.", ephemeral=True)
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
            return await interaction.response.send_message("Bot ses kanalında değil.", ephemeral=True)
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Duraklatıldı.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Devam ediyor.", ephemeral=True)
        else:
            await interaction.response.send_message("Şu an çalan bir şey yok.", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def atla(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc(interaction)
        p = self.player()
        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await interaction.response.send_message("Şu an çalan bir şey yok.", ephemeral=True)
        p.force_next = True
        vc.stop()
        await interaction.response.defer()

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def durdur(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc(interaction)
        p = self.player()
        if not vc:
            return await interaction.response.send_message("Bot ses kanalında değil.", ephemeral=True)
        p.queue.clear()
        p.current = None
        p.loop = False
        p.force_next = False
        try:
            await interaction.message.edit(embed=stopped_embed(), view=None)
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
        await interaction.response.send_message(f"🔉 Ses: **{int(p.volume * 100)}%**", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=1)
    async def ses_artir(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = self.vc(interaction)
        p = self.player()
        p.volume = min(2.0, round(p.volume + 0.1, 1))
        if vc and vc.source:
            vc.source.volume = p.volume
        await interaction.response.send_message(f"🔊 Ses: **{int(p.volume * 100)}%**", ephemeral=True)

    @discord.ui.button(emoji="🔁", label="Döngü", style=discord.ButtonStyle.secondary, row=1)
    async def dongu(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = self.player()
        p.loop = not p.loop
        durum = "açıldı 🔂" if p.loop else "kapatıldı"
        await interaction.response.send_message(f"Döngü **{durum}**.", ephemeral=True)

    @discord.ui.button(emoji="🔀", label="Karıştır", style=discord.ButtonStyle.secondary, row=1)
    async def karistir(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = self.player()
        if len(p.queue) < 2:
            return await interaction.response.send_message("Karıştırmak için en az 2 şarkı gerekli.", ephemeral=True)
        q = list(p.queue)
        random.shuffle(q)
        from collections import deque
        p.queue = deque(q)
        await interaction.response.send_message(f"🔀 {len(q)} şarkı karıştırıldı.", ephemeral=True)

    @discord.ui.button(emoji="📋", label="Sıra", style=discord.ButtonStyle.secondary, row=1)
    async def sira(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = self.player()
        if not p.current and not p.queue:
            return await interaction.response.send_message("Sıra boş.", ephemeral=True)
        embed = discord.Embed(title="📋 Müzik Sırası", color=discord.Color.blurple())
        if p.current:
            embed.add_field(
                name="▶️ Şu An",
                value=f"**[{p.current.title}]({p.current.webpage_url})** `{duration_fmt(p.current.duration)}`",
                inline=False,
            )
        for i, t in enumerate(list(p.queue)[:10], 1):
            embed.add_field(
                name=f"{i}. {t.title}",
                value=f"`{duration_fmt(t.duration)}` · {t.requester.mention}",
                inline=False,
            )
        if len(p.queue) > 10:
            embed.set_footer(text=f"ve {len(p.queue) - 10} şarkı daha...")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SearchButton(discord.ui.Button):
    def __init__(self, index: int, entry: dict, user: discord.Member, cog: "Music"):
        super().__init__(label=str(index), style=discord.ButtonStyle.primary)
        self.entry = entry
        self.user = user
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            return await interaction.response.send_message("Bu seçim size ait değil.", ephemeral=True)

        vc = await self.cog.ensure_voice(interaction)
        if not vc:
            return

        vid_id = self.entry.get("id", "")
        url = self.entry.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None)
        if not url:
            return await interaction.response.send_message("URL çözülemedi.", ephemeral=True)

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

        if vc.is_playing() or vc.is_paused():
            player.queue.append(track)
            await interaction.followup.send(
                embed=music_embed("Sıraya Eklendi", f"**{track.title}** sıraya eklendi."),
                ephemeral=True,
            )
        else:
            player.queue.appendleft(track)
            await self.cog._play_next(interaction.guild_id, vc)
            await interaction.followup.send(
                embed=music_embed("▶️ Çalıyor", f"**{track.title}**", discord.Color.green()),
                ephemeral=True,
            )
        self.view.stop()


class SearchView(discord.ui.View):
    def __init__(self, entries: list, user: discord.Member, cog: "Music"):
        super().__init__(timeout=30)
        self.entries = entries
        self.user = user
        self.cog = cog
        for i, entry in enumerate(entries):
            self.add_item(SearchButton(i + 1, entry, user, cog))
