import discord
from dataclasses import dataclass, field
from collections import deque
from .._v2 import c_text, c_section, c_container, c_thumbnail

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


def now_playing_card(track: Track, player: GuildPlayer) -> dict:
    lines = [
        "**▶️ Şimdi Çalıyor**",
        "",
        f"### [{track.title}]({track.webpage_url})",
        "",
        f"⏱️ **Süre:** `{duration_fmt(track.duration)}`",
        f"👤 **İsteyen:** {track.requester.mention}",
        f"🔊 **Ses:** `{int(player.volume * 100)}%`",
        f"🔁 **Döngü:** {'Açık 🔂' if player.loop else 'Kapalı'}",
        f"📋 **Sırada:** {len(player.queue)} şarkı",
    ]
    if player.queue:
        lines.append(f"⏭️ **Sonraki:** {list(player.queue)[0].title[:60]}")

    return c_container(
        c_section(
            c_text("\n".join(lines)),
            accessory=c_thumbnail(str(track.requester.display_avatar.url)),
        ),
        color=0x57F287,
    )


def stopped_card() -> dict:
    return c_container(
        c_text("**⏹️ Müzik Durduruldu**\n\nKuyruk bitti veya durduruldu."),
        color=0xED4245,
    )


