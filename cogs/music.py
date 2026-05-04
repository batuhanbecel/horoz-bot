import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque
from dataclasses import dataclass, field


YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": "in_playlist",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass
class Track:
    title: str
    url: str
    webpage_url: str
    duration: int
    requester: discord.Member


@dataclass
class GuildPlayer:
    queue: deque = field(default_factory=deque)
    current: Track | None = None
    volume: float = 0.5
    loop: bool = False


def duration_fmt(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def music_embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


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

    async def fetch_track(self, query: str, requester: discord.Member) -> Track | None:
        loop = asyncio.get_event_loop()
        opts = dict(YTDL_OPTIONS)
        opts["extract_flat"] = False
        opts["noplaylist"] = True

        def _fetch():
            with yt_dlp.YoutubeDL(opts) as ydl:
                if not query.startswith("http"):
                    info = ydl.extract_info(f"ytsearch:{query}", download=False)
                    if "entries" in info:
                        info = info["entries"][0]
                else:
                    info = ydl.extract_info(query, download=False)
                    if "entries" in info:
                        info = info["entries"][0]
                return info

        try:
            info = await loop.run_in_executor(None, _fetch)
            return Track(
                title=info.get("title", "Bilinmiyor"),
                url=info["url"],
                webpage_url=info.get("webpage_url", query),
                duration=info.get("duration", 0),
                requester=requester,
            )
        except Exception:
            return None

    def play_next(self, guild_id: int, vc: discord.VoiceClient):
        player = self.get_player(guild_id)
        if player.loop and player.current:
            track = player.current
        elif player.queue:
            track = player.queue.popleft()
            player.current = track
        else:
            player.current = None
            asyncio.run_coroutine_threadsafe(vc.disconnect(), self.bot.loop)
            return

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(track.url, **FFMPEG_OPTIONS),
            volume=player.volume,
        )
        vc.play(source, after=lambda e: self.play_next(guild_id, vc))

    music = app_commands.Group(name="müzik", description="Müzik komutları")

    # /müzik çal
    @music.command(name="çal", description="Bir şarkı veya YouTube URL'si çalar.")
    @app_commands.describe(sorgu="Şarkı adı veya YouTube linki")
    async def cal(self, interaction: discord.Interaction, sorgu: str):
        vc = await self.ensure_voice(interaction)
        if not vc:
            return

        await interaction.response.defer()
        track = await self.fetch_track(sorgu, interaction.user)

        if not track:
            await interaction.followup.send(
                embed=music_embed("Hata", "Şarkı bulunamadı.", discord.Color.red())
            )
            return

        player = self.get_player(interaction.guild_id)
        if vc.is_playing() or vc.is_paused():
            player.queue.append(track)
            await interaction.followup.send(
                embed=music_embed(
                    "Sıraya Eklendi",
                    f"**[{track.title}]({track.webpage_url})**\n"
                    f"Süre: `{duration_fmt(track.duration)}` | Sıra: #{len(player.queue)}",
                )
            )
        else:
            player.current = track
            self.play_next(interaction.guild_id, vc)
            await interaction.followup.send(
                embed=music_embed(
                    "Şimdi Çalıyor",
                    f"**[{track.title}]({track.webpage_url})**\n"
                    f"Süre: `{duration_fmt(track.duration)}` | İsteyen: {track.requester.mention}",
                    discord.Color.green(),
                )
            )

    # /müzik ara
    @music.command(name="ara", description="YouTube'da şarkı arar ve seçim sunar.")
    @app_commands.describe(sorgu="Aranacak şarkı")
    async def ara(self, interaction: discord.Interaction, sorgu: str):
        await interaction.response.defer(ephemeral=True)
        loop = asyncio.get_event_loop()

        def _search():
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                return ydl.extract_info(f"ytsearch5:{sorgu}", download=False)

        info = await loop.run_in_executor(None, _search)
        entries = info.get("entries", [])[:5]

        if not entries:
            await interaction.followup.send("Sonuç bulunamadı.", ephemeral=True)
            return

        embed = discord.Embed(title=f'"{sorgu}" için sonuçlar', color=discord.Color.blurple())
        for i, e in enumerate(entries, 1):
            dur = duration_fmt(e.get("duration", 0))
            embed.add_field(
                name=f"{i}. {e.get('title', 'Bilinmiyor')}",
                value=f"Süre: `{dur}` | [Link]({e.get('url', '')})",
                inline=False,
            )

        view = SearchView(entries, interaction.user, self)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # /müzik atla
    @music.command(name="atla", description="Mevcut şarkıyı atlar.")
    async def atla(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message(
                embed=music_embed("Hata", "Şu anda çalan bir şey yok.", discord.Color.red()), ephemeral=True
            )
            return
        vc.stop()
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
        await vc.disconnect()
        await interaction.response.send_message(embed=music_embed("Durduruldu", "Müzik durduruldu, kanaldan ayrıldım."))

    # /müzik ses
    @music.command(name="ses", description="Ses seviyesini ayarlar (0-200).")
    @app_commands.describe(seviye="Ses seviyesi (0-200)")
    async def ses(self, interaction: discord.Interaction, seviye: app_commands.Range[int, 0, 200]):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not vc.source:
            await interaction.response.send_message(
                embed=music_embed("Hata", "Şu anda çalan bir şey yok.", discord.Color.red()), ephemeral=True
            )
            return
        player = self.get_player(interaction.guild_id)
        player.volume = seviye / 100
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
                name="Şu An Çalıyor",
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
    @music.command(name="sıra-temizle", description="Müzik sırasını temizler.")
    async def sira_temizle(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        player.queue.clear()
        await interaction.response.send_message(
            embed=music_embed("Sıra Temizlendi", "Müzik sırası temizlendi.", discord.Color.green())
        )

    # /müzik döngü
    @music.command(name="döngü", description="Mevcut şarkı için döngü modunu açar/kapatır.")
    async def dongu(self, interaction: discord.Interaction):
        player = self.get_player(interaction.guild_id)
        player.loop = not player.loop
        durum = "açıldı" if player.loop else "kapatıldı"
        await interaction.response.send_message(
            embed=music_embed("Döngü", f"Döngü modu **{durum}**.", discord.Color.green())
        )


class SearchView(discord.ui.View):
    def __init__(self, entries: list, user: discord.Member, cog: Music):
        super().__init__(timeout=30)
        self.entries = entries
        self.user = user
        self.cog = cog
        for i in range(len(entries)):
            self.add_item(SearchButton(i + 1, entries[i], user, cog))


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
        await interaction.response.defer()
        url = self.entry.get("url") or self.entry.get("webpage_url", "")
        fake_interaction = interaction
        await self.cog.cal.callback(self.cog, fake_interaction, url)
        self.view.stop()


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
