import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import random
from collections import deque
from dataclasses import dataclass, field


YTDL_FLAT_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,
    "source_address": "0.0.0.0",
}

YTDL_STREAM_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

MAX_PLAYLIST = 100


@dataclass
class Track:
    title: str
    webpage_url: str
    requester: discord.Member
    duration: int = 0
    stream_url: str | None = None  # None = lazily resolved before playback


@dataclass
class GuildPlayer:
    queue: deque = field(default_factory=deque)
    current: Track | None = None
    volume: float = 0.5
    loop: bool = False


def duration_fmt(seconds: int) -> str:
    if not seconds:
        return "?"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def music_embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.timestamp = discord.utils.utcnow()
    return e


def is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def is_playlist_url(url: str) -> bool:
    return "list=" in url or "/playlist" in url


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
        """Şarkının akış URL'sini lazily çözer. Başarılıysa True döner."""
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
        """Tekil şarkı veya URL için Track döner."""
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
        """Playlist URL'sindeki tüm şarkıları (MAX_PLAYLIST kadar) flat olarak getirir."""
        loop = asyncio.get_running_loop()

        def _fetch():
            with yt_dlp.YoutubeDL(YTDL_FLAT_OPTIONS) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await loop.run_in_executor(None, _fetch)
        except Exception:
            return []

        entries = info.get("entries", [])[:MAX_PLAYLIST]
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

    # --- Playback engine ---

    def play_next(self, guild_id: int, vc: discord.VoiceClient):
        asyncio.run_coroutine_threadsafe(self._play_next(guild_id, vc), self.bot.loop)

    async def _play_next(self, guild_id: int, vc: discord.VoiceClient):
        if not vc.is_connected():
            return
        player = self.get_player(guild_id)

        if player.loop and player.current:
            # Döngü modunda aynı şarkıyı tekrar çal; stream URL yeniden çözülmeli
            track = player.current
            track.stream_url = None
        elif player.queue:
            track = player.queue.popleft()
            player.current = track
        else:
            player.current = None
            await vc.disconnect()
            return

        ok = await self.resolve_stream_url(track)
        if not ok:
            # Çözülemedi, bir sonrakine geç
            await self._play_next(guild_id, vc)
            return

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(track.stream_url, **FFMPEG_OPTIONS),
            volume=player.volume,
        )
        vc.play(source, after=lambda e: self.play_next(guild_id, vc))

    # --- Commands ---

    music = app_commands.Group(name="müzik", description="Müzik komutları")

    # /müzik çal
    @music.command(name="çal", description="Şarkı adı, YouTube URL'si veya playlist çalar.")
    @app_commands.describe(sorgu="Şarkı adı, YouTube linki veya playlist linki")
    async def cal(self, interaction: discord.Interaction, sorgu: str):
        vc = await self.ensure_voice(interaction)
        if not vc:
            return

        await interaction.response.defer()
        player = self.get_player(interaction.guild_id)
        is_playing_now = vc.is_playing() or vc.is_paused()

        # Playlist mi?
        if is_url(sorgu) and is_playlist_url(sorgu):
            tracks = await self.fetch_playlist(sorgu, interaction.user)
            if not tracks:
                await interaction.followup.send(
                    embed=music_embed("Hata", "Playlist bulunamadı veya boş.", discord.Color.red())
                )
                return

            for t in tracks:
                player.queue.append(t)

            if not is_playing_now:
                await self._play_next(interaction.guild_id, vc)
                embed = music_embed(
                    "Playlist Yüklendi",
                    f"**{len(tracks)}** şarkı yüklendi.\nİlk şarkı: **{tracks[0].title}**",
                    discord.Color.green(),
                )
            else:
                embed = music_embed(
                    "Playlist Sıraya Eklendi",
                    f"**{len(tracks)}** şarkı sıraya eklendi.",
                )
            await interaction.followup.send(embed=embed)
            return

        # Tekil şarkı
        track = await self.fetch_single(sorgu, interaction.user)
        if not track:
            await interaction.followup.send(
                embed=music_embed("Hata", "Şarkı bulunamadı.", discord.Color.red())
            )
            return

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
            # Kuyruğun başına ekle, _play_next halleder
            player.queue.appendleft(track)
            await self._play_next(interaction.guild_id, vc)
            await interaction.followup.send(
                embed=music_embed(
                    "Şimdi Çalıyor",
                    f"**[{track.title}]({track.webpage_url})**\n"
                    f"Süre: `{duration_fmt(track.duration)}` | İsteyen: {track.requester.mention}",
                    discord.Color.green(),
                )
            )

    # /müzik ara
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
            await interaction.followup.send("Sonuç bulunamadı.", ephemeral=True)
            return

        embed = discord.Embed(title=f'"{sorgu}" için sonuçlar', color=discord.Color.blurple())
        for i, e in enumerate(entries, 1):
            dur = duration_fmt(e.get("duration", 0))
            url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id', '')}"
            embed.add_field(
                name=f"{i}. {e.get('title', 'Bilinmiyor')}",
                value=f"Süre: `{dur}` | [Link]({url})",
                inline=False,
            )

        view = SearchView(entries, interaction.user, self)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # /müzik atla
    @music.command(name="atla", description="Mevcut şarkıyı atlar.")
    async def atla(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            await interaction.response.send_message(
                embed=music_embed("Hata", "Şu anda çalan bir şey yok.", discord.Color.red()), ephemeral=True
            )
            return
        player = self.get_player(interaction.guild_id)
        # Döngü modunu geçici olarak kapat ki atla çalışsın
        was_loop = player.loop
        player.loop = False
        vc.stop()
        player.loop = was_loop
        await interaction.response.send_message(embed=music_embed("Atlandı", "Şarkı atlandı.", discord.Color.green()))

    # /müzik duraklat
    @music.command(name="duraklat", description="Çalmayı duraklatır.")
    async def duraklat(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message(
                embed=music_embed("Hata", "Şu anda çalan bir şey yok.", discord.Color.red()), ephemeral=True
            )
            return
        vc.pause()
        await interaction.response.send_message(embed=music_embed("Duraklatıldı", "Müzik duraklatıldı."))

    # /müzik devam
    @music.command(name="devam", description="Duraklatılmış müziği devam ettirir.")
    async def devam(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not vc.is_paused():
            await interaction.response.send_message(
                embed=music_embed("Hata", "Duraklatılmış bir şey yok.", discord.Color.red()), ephemeral=True
            )
            return
        vc.resume()
        await interaction.response.send_message(embed=music_embed("Devam", "Müzik devam ediyor.", discord.Color.green()))

    # /müzik dur
    @music.command(name="dur", description="Müziği durdurur ve kanaldan ayrılır.")
    async def dur(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message(
                embed=music_embed("Hata", "Bot bir ses kanalında değil.", discord.Color.red()), ephemeral=True
            )
            return
        player = self.get_player(interaction.guild_id)
        player.queue.clear()
        player.current = None
        player.loop = False
        await vc.disconnect()
        await interaction.response.send_message(embed=music_embed("Durduruldu", "Müzik durduruldu, kanaldan ayrıldım."))

    # /müzik ses
    @music.command(name="ses", description="Ses seviyesini ayarlar (0-200).")
    @app_commands.describe(seviye="Ses seviyesi (0-200)")
    async def ses(self, interaction: discord.Interaction, seviye: app_commands.Range[int, 0, 200]):
        vc: discord.VoiceClient = interaction.guild.voice_client
        player = self.get_player(interaction.guild_id)
        player.volume = seviye / 100
        if vc and vc.source:
            vc.source.volume = player.volume
        await interaction.response.send_message(
            embed=music_embed("Ses Seviyesi", f"Ses seviyesi **{seviye}%** olarak ayarlandı.", discord.Color.green())
        )

    # /müzik sıra
    @music.command(name="sıra", description="Mevcut müzik sırasını gösterir.")
    async def sira(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if not player.current and not player.queue:
            await interaction.response.send_message(
                embed=music_embed("Sıra", "Sıra boş.", discord.Color.orange()), ephemeral=True
            )
            return

        embed = discord.Embed(title="Müzik Sırası", color=discord.Color.blurple())
        if player.current:
            embed.add_field(
                name="▶️ Şu An Çalıyor",
                value=f"**[{player.current.title}]({player.current.webpage_url})** | `{duration_fmt(player.current.duration)}`",
                inline=False,
            )
        for i, t in enumerate(list(player.queue)[:10], 1):
            embed.add_field(
                name=f"{i}. {t.title}",
                value=f"`{duration_fmt(t.duration)}` | {t.requester.mention}",
                inline=False,
            )
        if len(player.queue) > 10:
            embed.set_footer(text=f"ve {len(player.queue) - 10} şarkı daha...")
        await interaction.response.send_message(embed=embed)

    # /müzik sıra-temizle
    @music.command(name="sıra-temizle", description="Müzik sırasını temizler (mevcut şarkıyı durdurmaz).")
    async def sira_temizle(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        count = len(player.queue)
        player.queue.clear()
        await interaction.response.send_message(
            embed=music_embed("Sıra Temizlendi", f"{count} şarkı sıradan kaldırıldı.", discord.Color.green())
        )

    # /müzik karıştır
    @music.command(name="karıştır", description="Müzik sırasını rastgele karıştırır.")
    async def karistir(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if len(player.queue) < 2:
            await interaction.response.send_message(
                embed=music_embed("Hata", "Karıştırmak için sırada en az 2 şarkı olmalı.", discord.Color.red()),
                ephemeral=True,
            )
            return
        queue_list = list(player.queue)
        random.shuffle(queue_list)
        player.queue = deque(queue_list)
        await interaction.response.send_message(
            embed=music_embed("Karıştırıldı", f"{len(queue_list)} şarkı rastgele sıralandı. 🔀", discord.Color.green())
        )

    # /müzik döngü
    @music.command(name="döngü", description="Mevcut şarkı için döngü modunu açar/kapatır.")
    async def dongu(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        player.loop = not player.loop
        durum = "açıldı 🔂" if player.loop else "kapatıldı"
        await interaction.response.send_message(
            embed=music_embed("Döngü", f"Döngü modu **{durum}**.", discord.Color.green())
        )

    # /müzik şimdi-çalıyor
    @music.command(name="şimdi-çalıyor", description="Şu an çalan şarkıyı gösterir.")
    async def simdi_calıyor(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        if not player.current:
            await interaction.response.send_message(
                embed=music_embed("Şimdi Çalıyor", "Şu an çalan bir şey yok.", discord.Color.orange()),
                ephemeral=True,
            )
            return
        t = player.current
        embed = music_embed(
            "▶️ Şimdi Çalıyor",
            f"**[{t.title}]({t.webpage_url})**\n"
            f"Süre: `{duration_fmt(t.duration)}` | İsteyen: {t.requester.mention}\n"
            f"Döngü: {'Açık 🔂' if player.loop else 'Kapalı'} | Ses: {int(player.volume * 100)}%",
            discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)


class SearchView(discord.ui.View):
    def __init__(self, entries: list, user: discord.Member, cog: Music):
        super().__init__(timeout=30)
        self.entries = entries
        self.user = user
        self.cog = cog
        for i, entry in enumerate(entries):
            self.add_item(SearchButton(i + 1, entry, user, cog))


class SearchButton(discord.ui.Button):
    def __init__(self, index: int, entry: dict, user: discord.Member, cog: Music):
        super().__init__(label=str(index), style=discord.ButtonStyle.primary)
        self.entry = entry
        self.user = user
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("Bu seçim size ait değil.", ephemeral=True)
            return

        vc = await self.cog.ensure_voice(interaction)
        if not vc:
            return

        vid_id = self.entry.get("id", "")
        url = self.entry.get("url") or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None)
        if not url:
            await interaction.response.send_message("URL çözülemedi.", ephemeral=True)
            return

        await interaction.response.defer()
        player = self.cog.get_player(interaction.guild_id)
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
                embed=music_embed("Sıraya Eklendi", f"**{track.title}** sıraya eklendi.", discord.Color.blurple()),
                ephemeral=True,
            )
        else:
            player.queue.appendleft(track)
            await self.cog._play_next(interaction.guild_id, vc)
            await interaction.followup.send(
                embed=music_embed("Şimdi Çalıyor", f"**{track.title}**", discord.Color.green()),
                ephemeral=True,
            )
        self.view.stop()


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
