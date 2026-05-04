import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import random
from collections import deque
from ._shared import (
    YTDL_FLAT_OPTIONS, YTDL_STREAM_OPTIONS, FFMPEG_OPTIONS, MAX_PLAYLIST,
    Track, GuildPlayer, duration_fmt, is_url, is_playlist_url, music_embed, now_playing_embed,
)
from .views import PlayerView, SearchView


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
            await interaction.response.send_message(
                embed=music_embed("Hata", "Bir ses kanalında olmanız gerekiyor.", discord.Color.red()),
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
            player.player_message = await channel.send(
                embed=now_playing_embed(track, player),
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
                return await interaction.followup.send(
                    embed=music_embed("Hata", "Playlist bulunamadı veya boş.", discord.Color.red())
                )
            for t in tracks:
                player.queue.append(t)
            if not is_playing_now:
                await self._play_next(interaction.guild_id, vc)
                msg = music_embed("Playlist Yüklendi", f"**{len(tracks)}** şarkı yüklendi.", discord.Color.green())
            else:
                msg = music_embed("Playlist Sıraya Eklendi", f"**{len(tracks)}** şarkı sıraya eklendi.")
            return await interaction.followup.send(embed=msg)

        track = await self.fetch_single(sorgu, interaction.user)
        if not track:
            return await interaction.followup.send(
                embed=music_embed("Hata", "Şarkı bulunamadı.", discord.Color.red())
            )

        if is_playing_now:
            player.queue.append(track)
            await interaction.followup.send(
                embed=music_embed(
                    "Sıraya Eklendi",
                    f"**[{track.title}]({track.webpage_url})**\n"
                    f"Süre: `{duration_fmt(track.duration)}` | Sıra: #{len(player.queue)}",
                )
            )
        else:
            player.queue.appendleft(track)
            await self._play_next(interaction.guild_id, vc)
            await interaction.followup.send(
                embed=music_embed("✅ Eklendi", f"**{track.title}** çalmaya başlıyor.", discord.Color.green())
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
            return await interaction.followup.send("Sonuç bulunamadı.", ephemeral=True)

        embed = discord.Embed(title=f'"{sorgu}" için sonuçlar', color=discord.Color.blurple())
        for i, e in enumerate(entries, 1):
            url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id', '')}"
            embed.add_field(
                name=f"{i}. {e.get('title', 'Bilinmiyor')}",
                value=f"Süre: `{duration_fmt(e.get('duration', 0))}` | [Link]({url})",
                inline=False,
            )
        embed.timestamp = discord.utils.utcnow()
        await interaction.followup.send(embed=embed, view=SearchView(entries, interaction.user, self), ephemeral=True)

    @music.command(name="atla", description="Mevcut şarkıyı atlar.")
    async def atla(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await interaction.response.send_message(
                embed=music_embed("Hata", "Şu anda çalan bir şey yok.", discord.Color.red()), ephemeral=True
            )
        p = self.get_player(interaction.guild_id)
        p.force_next = True
        vc.stop()
        await interaction.response.send_message(embed=music_embed("⏭️ Atlandı", "Şarkı atlandı.", discord.Color.green()))

    @music.command(name="duraklat", description="Çalmayı duraklatır.")
    async def duraklat(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return await interaction.response.send_message(
                embed=music_embed("Hata", "Şu anda çalan bir şey yok.", discord.Color.red()), ephemeral=True
            )
        vc.pause()
        await interaction.response.send_message(embed=music_embed("⏸️ Duraklatıldı", ""))

    @music.command(name="devam", description="Duraklatılmış müziği devam ettirir.")
    async def devam(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not vc.is_paused():
            return await interaction.response.send_message(
                embed=music_embed("Hata", "Duraklatılmış bir şey yok.", discord.Color.red()), ephemeral=True
            )
        vc.resume()
        await interaction.response.send_message(embed=music_embed("▶️ Devam", "Müzik devam ediyor.", discord.Color.green()))

    @music.command(name="dur", description="Müziği durdurur ve kanaldan ayrılır.")
    async def dur(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message(
                embed=music_embed("Hata", "Bot bir ses kanalında değil.", discord.Color.red()), ephemeral=True
            )
        p = self.get_player(interaction.guild_id)
        p.queue.clear()
        p.current = None
        p.loop = False
        await self._clear_player_message(p)
        await vc.disconnect()
        await interaction.response.send_message(embed=music_embed("⏹️ Durduruldu", "Müzik durduruldu, kanaldan ayrıldım."))

    @music.command(name="ses", description="Ses seviyesini ayarlar (0-200).")
    @app_commands.describe(seviye="Ses seviyesi (0-200)")
    async def ses(self, interaction: discord.Interaction, seviye: app_commands.Range[int, 0, 200]):
        vc: discord.VoiceClient = interaction.guild.voice_client
        p = self.get_player(interaction.guild_id)
        p.volume = seviye / 100
        if vc and vc.source:
            vc.source.volume = p.volume
        await interaction.response.send_message(
            embed=music_embed("🔊 Ses Seviyesi", f"**{seviye}%** olarak ayarlandı.", discord.Color.green())
        )

    @music.command(name="sıra", description="Mevcut müzik sırasını gösterir.")
    async def sira(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        if not p.current and not p.queue:
            return await interaction.response.send_message(
                embed=music_embed("Sıra", "Sıra boş.", discord.Color.orange()), ephemeral=True
            )
        embed = discord.Embed(title="📋 Müzik Sırası", color=discord.Color.blurple())
        if p.current:
            embed.add_field(
                name="▶️ Şu An Çalıyor",
                value=f"**[{p.current.title}]({p.current.webpage_url})** | `{duration_fmt(p.current.duration)}`",
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
        await interaction.response.send_message(embed=embed)

    @music.command(name="sıra-sil", description="Müzik sırasını temizler.")
    async def sira_sil(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        count = len(p.queue)
        p.queue.clear()
        await interaction.response.send_message(
            embed=music_embed("Sıra Temizlendi", f"{count} şarkı kaldırıldı.", discord.Color.green())
        )

    @music.command(name="karıştır", description="Müzik sırasını rastgele karıştırır.")
    async def karistir(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        if len(p.queue) < 2:
            return await interaction.response.send_message(
                embed=music_embed("Hata", "Karıştırmak için en az 2 şarkı gerekli.", discord.Color.red()), ephemeral=True
            )
        q = list(p.queue)
        random.shuffle(q)
        p.queue = deque(q)
        await interaction.response.send_message(
            embed=music_embed("🔀 Karıştırıldı", f"{len(q)} şarkı rastgele sıralandı.", discord.Color.green())
        )

    @music.command(name="döngü", description="Döngü modunu açar/kapatır.")
    async def dongu(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        p.loop = not p.loop
        durum = "açıldı 🔂" if p.loop else "kapatıldı"
        await interaction.response.send_message(
            embed=music_embed("🔁 Döngü", f"Döngü modu **{durum}**.", discord.Color.green())
        )

    @music.command(name="şimdi", description="Şu an çalan şarkıyı gösterir.")
    async def simdi(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        if not p.current:
            return await interaction.response.send_message(
                embed=music_embed("Şimdi Çalıyor", "Şu an çalan bir şey yok.", discord.Color.orange()), ephemeral=True
            )
        await interaction.response.send_message(
            embed=now_playing_embed(p.current, p),
            view=PlayerView(self, interaction.guild_id),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
