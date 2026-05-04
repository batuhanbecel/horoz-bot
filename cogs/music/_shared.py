import discord
from dataclasses import dataclass, field
from collections import deque

YTDL_FLAT_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "ignoreerrors": True,
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
    stream_url: str | None = None


@dataclass
class GuildPlayer:
    queue: deque = field(default_factory=deque)
    current: Track | None = None
    volume: float = 0.5
    loop: bool = False
    force_next: bool = False
    text_channel_id: int | None = None
    player_message: discord.Message | None = None
    history: deque = field(default_factory=lambda: deque(maxlen=10))


def duration_fmt(seconds: int) -> str:
    if not seconds:
        return "?"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def is_playlist_url(url: str) -> bool:
    return "list=" in url or "/playlist" in url


def now_playing_embed(track: Track, player: GuildPlayer) -> discord.Embed:
    e = discord.Embed(
        title="▶️ Şimdi Çalıyor",
        description=f"### [{track.title}]({track.webpage_url})",
        color=discord.Color.green(),
    )
    e.add_field(name="⏱️ Süre",    value=f"`{duration_fmt(track.duration)}`", inline=True)
    e.add_field(name="👤 İsteyen", value=track.requester.mention,             inline=True)
    e.add_field(name="🔊 Ses",     value=f"`{int(player.volume * 100)}%`",    inline=True)
    e.add_field(name="🔁 Döngü",   value="Açık 🔂" if player.loop else "Kapalı", inline=True)
    e.add_field(name="📋 Sırada",  value=f"{len(player.queue)} şarkı",        inline=True)
    if player.queue:
        e.add_field(name="⏭️ Sonraki", value=list(player.queue)[0].title[:60], inline=True)
    e.set_thumbnail(url=track.requester.display_avatar.url)
    e.timestamp = discord.utils.utcnow()
    return e


def stopped_embed() -> discord.Embed:
    e = discord.Embed(
        title="⏹️ Müzik Durduruldu",
        description="Kuyruk bitti veya durduruldu.",
        color=discord.Color.red(),
    )
    e.timestamp = discord.utils.utcnow()
    return e


def music_embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.timestamp = discord.utils.utcnow()
    return e
