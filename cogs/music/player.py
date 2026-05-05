import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import random
from collections import deque
from ._shared import (
    YTDL_FLAT_OPTIONS, YTDL_STREAM_OPTIONS, FFMPEG_OPTIONS, MAX_PLAYLIST,
    Track, GuildPlayer, duration_fmt, is_url, is_playlist_url, music_embed,
    now_playing_card,
)
from .views import PlayerView, SearchView
from .._v2 import c_text, c_container, c_separator, channel_send as v2_channel_send, followup as v2_followup, respond


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer()
        return self.players[guild_id]

    async def ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await respond(interaction,
                c_container(c_text("**❌ Ses Kanalı Gerekli**\n\nBir ses kanalında olmanız gerekiyor."), color=0xED4245),
                ephemeral=True,
            )
            return None
        vc: discord.VoiceClient = interaction.guild.voice_client
        if vc is None:
            vc = await interaction.user.voice.channel.connect()
        elif vc.channel != interaction.user.voice.channel:
            await vc.move_to(interaction.user.voice.channel)
        return vc

    async def resolve_stream_url(self, track: Track) -> bool:
        if track.stream_url:
            return True
        loop = asyncio.get_running_loop()

        def _fetch():
            with yt_dlp.YoutubeDL(YTDL_STREAM_OPTIONS) as ydl:
                info = ydl.extract_info(track.webpage_url, download=False)
                return info.get("url"), info.get("duration", 0), info.get("title", track.title)

        try:
            stream_url, duration, title = await loop.run_in_executor(None, _fetch)
            track.stream_url = stream_url
            track.duration = duration
            track.title = title
            return bool(stream_url)
        except Exception:
            return False

    async def fetch_single(self, query: str, requester: discord.Member) -> Track | None:
        loop = asyncio.get_running_loop()

        def _fetch():
            with yt_dlp.YoutubeDL(YTDL_STREAM_OPTIONS) as ydl:
                search = f"ytsearch:{query}" if not is_url(query) else query
                info = ydl.extract_info(search, download=False)
                if "entries" in info:
                    info = info["entries"][0]
                return info

        try:
            info = await loop.run_in_executor(None, _fetch)
            return Track(
                title=info.get("title", "Bilinmiyor"),
                webpage_url=info.get("webpage_url", query),
                requester=requester,
                duration=info.get("duration", 0),
                stream_url=info.get("url"),
            )
        except Exception:
            return None

    async def fetch_playlist(self, url: str, requester: discord.Member) -> list[Track]:
        loop = asyncio.get_running_loop()

        def _fetch():
            with yt_dlp.YoutubeDL(YTDL_FLAT_OPTIONS) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await loop.run_in_executor(None, _fetch)
        except Exception as e:
            print(f"[fetch_playlist] Hata: {e}")
            return []

        if not info:
            return []
        entries = (info.get("entries") or [])[:MAX_PLAYLIST]
        tracks = []
        for e in entries:
            if not e:
                continue
            vid_id = e.get("id", "")
            webpage = (
                e.get("webpage_url")
                or e.get("url")
                or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None)
            )
            if not webpage:
                continue
            tracks.append(Track(
                title=e.get("title", "Bilinmiyor"),
                webpage_url=webpage,
                requester=requester,
                duration=e.get("duration", 0),
                stream_url=None,
            ))
        return tracks

    # ── Playback engine ────────────────────────────────────────────────────────

    def play_next(self, guild_id: int, vc: discord.VoiceClient):
        asyncio.run_coroutine_threadsafe(self._play_next(guild_id, vc), self.bot.loop)

    async def _play_next(self, guild_id: int, vc: discord.VoiceClient):
        if not vc.is_connected():
            return
        player = self.get_player(guild_id)

        if player.loop and player.current and not player.force_next:
            track = player.current
            track.stream_url = None
        elif player.queue:
            player.force_next = False
            if player.current:
                player.history.append(player.current)
            track = player.queue.popleft()
            player.current = track
        else:
            player.current = None
            await self._clear_player_message(player)
            await vc.disconnect()
            return

        ok = await self.resolve_stream_url(track)
        if not ok:
            await self._play_next(guild_id, vc)
            return

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(track.stream_url, **FFMPEG_OPTIONS),
            volume=player.volume,
        )
        vc.play(source, after=lambda e: self.play_next(guild_id, vc))
        await self._send_player_message(guild_id, track, player)

    async def _send_player_message(self, guild_id: int, track: Track, player: GuildPlayer):
        await self._clear_player_message(player)
        if not player.text_channel_id:
            return
        channel = self.bot.get_channel(player.text_channel_id)
        if not channel:
            return
        try:
            player.player_message = await v2_channel_send(
                channel,
                now_playing_card(track, player),
                view=PlayerView(self, guild_id),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _clear_player_message(self, player: GuildPlayer):
        if player.player_message:
            try:
                await player.player_message.delete()
            except (discord.NotFound, discord.HTTPException):
                pass
            player.player_message = None

    # ── Commands ───────────────────────────────────────────────────────────────

    music = app_commands.Group(name="müzik", description="Müzik komutları")

    @music.command(name="çal", description="Şarkı adı, YouTube URL'si veya playlist çalar.")
    @app_commands.describe(sorgu="Şarkı adı, YouTube linki veya playlist linki")
    async def cal(self, interaction: discord.Interaction, sorgu: str):
        vc = await self.ensure_voice(interaction)
        if not vc:
            return

        await interaction.response.defer()
        player = self.get_player(interaction.guild_id)
        player.text_channel_id = interaction.channel_id
        is_playing_now = vc.is_playing() or vc.is_paused()

        if is_url(sorgu) and is_playlist_url(sorgu):
            tracks = await self.fetch_playlist(sorgu, interaction.user)
            if not tracks:
                return await v2_followup(interaction,
                    c_container(c_text("**❌ Hata**\n\nPlaylist bulunamadı veya boş."), color=0xED4245),
                )
            for t in tracks:
                player.queue.append(t)
            if not is_playing_now:
                await self._play_next(interaction.guild_id, vc)
                await v2_followup(interaction,
                    c_container(c_text(f"**✅ Playlist Yüklendi**\n\n**{len(tracks)}** şarkı yüklendi."), color=0x57F287),
                )
            else:
                await v2_followup(interaction,
                    c_container(c_text(f"**📋 Playlist Sıraya Eklendi**\n\n**{len(tracks)}** şarkı sıraya eklendi."), color=0x5865F2),
                )
            return

        track = await self.fetch_single(sorgu, interaction.user)
        if not track:
            return await v2_followup(interaction,
                c_container(c_text("**❌ Hata**\n\nŞarkı bulunamadı."), color=0xED4245),
            )

        if is_playing_now:
            player.queue.append(track)
            await v2_followup(interaction,
                c_container(
                    c_text(
                        f"**📋 Sıraya Eklendi**\n\n"
                        f"**[{track.title}]({track.webpage_url})**\n"
                        f"⏱️ `{duration_fmt(track.duration)}` · #{len(player.queue)}"
                    ),
                    color=0x5865F2,
                ),
            )
        else:
            player.queue.appendleft(track)
            await self._play_next(interaction.guild_id, vc)
            await v2_followup(interaction,
                c_container(c_text(f"**✅ Eklendi**\n\n**{track.title}** çalmaya başlıyor."), color=0x57F287),
            )

    @music.command(name="ara", description="YouTube'da şarkı arar ve 5 sonuç listeler.")
    @app_commands.describe(sorgu="Aranacak şarkı")
    async def ara(self, interaction: discord.Interaction, sorgu: str):
        await interaction.response.defer(ephemeral=True)
        loop = asyncio.get_running_loop()

        def _search():
            opts = dict(YTDL_FLAT_OPTIONS)
            opts["noplaylist"] = True
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(f"ytsearch5:{sorgu}", download=False)

        info = await loop.run_in_executor(None, _search)
        entries = [e for e in info.get("entries", []) if e][:5]

        if not entries:
            return await v2_followup(interaction,
                c_container(c_text("**❌ Sonuç Bulunamadı**\n\nArama için sonuç yok."), color=0xED4245),
                ephemeral=True,
            )

        lines = [f'**🔍 "{sorgu}" için sonuçlar**', ""]
        for i, e in enumerate(entries, 1):
            url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id', '')}"
            lines.append(f"`{i}.` **[{e.get('title', 'Bilinmiyor')}]({url})** · `{duration_fmt(e.get('duration', 0))}`")

        await v2_followup(interaction,
            c_container(c_text("\n".join(lines)), color=0x5865F2),
            view=SearchView(entries, interaction.user, self),
            ephemeral=True,
        )

    @music.command(name="atla", description="Mevcut şarkıyı atlar.")
    async def atla(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await respond(interaction,
                c_container(c_text("**❌ Hata**\n\nŞu anda çalan bir şey yok."), color=0xED4245),
                ephemeral=True,
            )
        p = self.get_player(interaction.guild_id)
        p.force_next = True
        vc.stop()
        await respond(interaction,
            c_container(c_text("**⏭️ Atlandı**\n\nŞarkı atlandı."), color=0x57F287),
        )

    @music.command(name="duraklat", description="Çalmayı duraklatır.")
    async def duraklat(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await respond(interaction,
                c_container(c_text("**❌ Hata**\n\nŞu anda çalan bir şey yok."), color=0xED4245),
                ephemeral=True,
            )
        vc.pause()
        await respond(interaction,
            c_container(c_text("**⏸️ Duraklatıldı**"), color=0xF0A030),
        )

    @music.command(name="devam", description="Duraklatılmış müziği devam ettirir.")
    async def devam(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not vc.is_paused():
            return await respond(interaction,
                c_container(c_text("**❌ Hata**\n\nDuraklatılmış bir şey yok."), color=0xED4245),
                ephemeral=True,
            )
        vc.resume()
        await respond(interaction,
            c_container(c_text("**▶️ Devam**\n\nMüzik devam ediyor."), color=0x57F287),
        )

    @music.command(name="dur", description="Müziği durdurur ve kanaldan ayrılır.")
    async def dur(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc:
            return await respond(interaction,
                c_container(c_text("**❌ Hata**\n\nBot bir ses kanalında değil."), color=0xED4245),
                ephemeral=True,
            )
        p = self.get_player(interaction.guild_id)
        p.queue.clear()
        p.current = None
        p.loop = False
        await self._clear_player_message(p)
        await vc.disconnect()
        await respond(interaction,
            c_container(c_text("**⏹️ Durduruldu**\n\nMüzik durduruldu, kanaldan ayrıldım."), color=0xED4245),
        )

    @music.command(name="ses", description="Ses seviyesini ayarlar (0-200).")
    @app_commands.describe(seviye="Ses seviyesi (0-200)")
    async def ses(self, interaction: discord.Interaction, seviye: app_commands.Range[int, 0, 200]):
        vc: discord.VoiceClient = interaction.guild.voice_client
        p = self.get_player(interaction.guild_id)
        p.volume = seviye / 100
        if vc and vc.source:
            vc.source.volume = p.volume
        await respond(interaction,
            c_container(c_text(f"**🔊 Ses Seviyesi**\n\n**{seviye}%** olarak ayarlandı."), color=0x57F287),
        )

    @music.command(name="sıra", description="Mevcut müzik sırasını gösterir.")
    async def sira(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        if not p.current and not p.queue:
            return await respond(interaction,
                c_container(c_text("**📋 Sıra**\n\nSıra boş."), color=0xF0A030),
                ephemeral=True,
            )
        lines = ["**📋 Müzik Sırası**", ""]
        if p.current:
            lines.append(f"▶️ **Şu An Çalıyor:** [{p.current.title}]({p.current.webpage_url}) | `{duration_fmt(p.current.duration)}`")
            lines.append("")
        for i, t in enumerate(list(p.queue)[:10], 1):
            lines.append(f"`{i}.` {t.title} · `{duration_fmt(t.duration)}` · {t.requester.mention}")
        if len(p.queue) > 10:
            lines.append(f"\n-# ve {len(p.queue) - 10} şarkı daha...")
        await respond(interaction,
            c_container(c_text("\n".join(lines)), color=0x5865F2),
        )

    @music.command(name="sıra-sil", description="Müzik sırasını temizler.")
    async def sira_sil(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        count = len(p.queue)
        p.queue.clear()
        await respond(interaction,
            c_container(c_text(f"**🗑️ Sıra Temizlendi**\n\n{count} şarkı kaldırıldı."), color=0x57F287),
        )

    @music.command(name="karıştır", description="Müzik sırasını rastgele karıştırır.")
    async def karistir(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        if len(p.queue) < 2:
            return await respond(interaction,
                c_container(c_text("**❌ Hata**\n\nKarıştırmak için en az 2 şarkı gerekli."), color=0xED4245),
                ephemeral=True,
            )
        q = list(p.queue)
        random.shuffle(q)
        p.queue = deque(q)
        await respond(interaction,
            c_container(c_text(f"**🔀 Karıştırıldı**\n\n{len(q)} şarkı rastgele sıralandı."), color=0x57F287),
        )

    @music.command(name="döngü", description="Döngü modunu açar/kapatır.")
    async def dongu(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        p.loop = not p.loop
        durum = "açıldı 🔂" if p.loop else "kapatıldı"
        await respond(interaction,
            c_container(c_text(f"**🔁 Döngü**\n\nDöngü modu **{durum}**."), color=0x57F287),
        )

    @music.command(name="şimdi", description="Şu an çalan şarkıyı gösterir.")
    async def simdi(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        if not p.current:
            return await respond(interaction,
                c_container(c_text("**🎵 Şimdi Çalıyor**\n\nŞu an çalan bir şey yok."), color=0xF0A030),
                ephemeral=True,
            )
        await respond(interaction,
            now_playing_card(p.current, p),
            view=PlayerView(self, interaction.guild_id),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
