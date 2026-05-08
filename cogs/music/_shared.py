import discord
import re
from dataclasses import dataclass, field
from collections import deque
from .._v2 import (
    COLORS, c_text, c_section, c_container, c_thumbnail, c_separator, c_card,
)

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

_YT_ID_RE = re.compile(r"(?:v=|youtu\.be/|/embed/|/shorts/)([\w-]{11})")


@dataclass
class Track:
    title: str
    webpage_url: str
    requester: discord.Member
    duration: int = 0
    stream_url: str | None = None
    platform: str = "youtube"          # youtube / spotify / soundcloud / other
    source_url: str | None = None      # platform == 'spotify' → orjinal Spotify URL


@dataclass
class GuildPlayer:
    queue: deque = field(default_factory=deque)
    current: Track | None = None
    volume: float = 0.5
    loop: bool = False
    paused: bool = False
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


def yt_thumbnail(url: str) -> str | None:
    """YouTube URL'inden video thumbnail URL'i üretir."""
    m = _YT_ID_RE.search(url)
    if m:
        return f"https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg"
    return None


# ── Platform tespiti & etiketleri ─────────────────────────────────────────────

_PLATFORM_LABELS = {
    "youtube":    "<:youtube:0> YouTube",  # discord emoji ID yoksa fallback altta
    "spotify":    "🟢 Spotify",
    "soundcloud": "🟠 SoundCloud",
    "twitch":     "🟣 Twitch",
    "vimeo":      "🔵 Vimeo",
    "bandcamp":   "🟫 Bandcamp",
    "other":      "🌐 Diğer",
}

# Custom emoji ID yoksa unicode fallback
_PLATFORM_LABELS_FALLBACK = {
    "youtube":    "▶️ YouTube",
    "spotify":    "🟢 Spotify",
    "soundcloud": "🟠 SoundCloud",
    "twitch":     "🟣 Twitch",
    "vimeo":      "🔵 Vimeo",
    "bandcamp":   "🟫 Bandcamp",
    "other":      "🌐 Diğer",
}


def detect_platform(url: str) -> str:
    """URL'den platform tespiti."""
    if not url:
        return "other"
    url_l = url.lower()
    if "open.spotify.com" in url_l:
        return "spotify"
    if "youtube.com" in url_l or "youtu.be" in url_l or "music.youtube" in url_l:
        return "youtube"
    if "soundcloud.com" in url_l:
        return "soundcloud"
    if "twitch.tv" in url_l:
        return "twitch"
    if "vimeo.com" in url_l:
        return "vimeo"
    if "bandcamp.com" in url_l:
        return "bandcamp"
    return "other"


def platform_label(platform: str) -> str:
    """Platform için Discord emoji + isim etiketi."""
    return _PLATFORM_LABELS_FALLBACK.get(platform, _PLATFORM_LABELS_FALLBACK["other"])


def now_playing_card(track: Track, player: GuildPlayer) -> dict:
    """Müzik çalar kartı: thumbnail + başlık + meta + badges. Player state'ine göre dinamik."""
    thumb = yt_thumbnail(track.webpage_url) or str(track.requester.display_avatar.url)
    duration = duration_fmt(track.duration)
    loop_str = "🔂 Açık" if player.loop else "➡️ Kapalı"

    # Durum (paused / playing) — başlık ve renk değişir
    if player.paused:
        title = "⏸️ Duraklatıldı"
        color = COLORS.WARNING
    else:
        title = "▶️ Şimdi Çalıyor"
        color = COLORS.MUSIC

    # Platform badge
    source_badge = platform_label(track.platform).replace(" ", " · ")
    badges = [source_badge]
    if player.loop:
        badges.append("🔂 Döngü")
    if track.platform == "spotify":
        badges.append("🟢 Spotify Bridge")

    # Platform göstergesi
    platform_line = f"🎧 **Kaynak:** {platform_label(track.platform)}"
    if track.platform == "spotify" and track.source_url:
        platform_line += f"  ·  [Spotify]({track.source_url})"

    items: list[dict] = [
        c_section(
            c_text(f"## {title}\n### [{track.title}]({track.webpage_url})"),
            accessory=c_thumbnail(thumb),
        ),
        c_separator(),
        c_text(" · ".join(badges)),
        c_separator(),
        c_text(
            f"⏱️ **Süre:** `{duration}`\n"
            f"👤 **İsteyen:** {track.requester.mention}\n"
            f"{platform_line}\n"
            f"🔊 **Ses:** `{int(player.volume * 100)}%` · "
            f"🔁 **Döngü:** {loop_str} · "
            f"📋 **Sırada:** `{len(player.queue)}` şarkı"
        ),
    ]

    if player.queue:
        next_track = list(player.queue)[0]
        items.append(c_separator())
        items.append(c_text(f"⏭️ **Sonraki:** {next_track.title[:60]}"))

    return c_container(*items, color=color)


def stopped_card() -> dict:
    return c_card("## ⏹️ Müzik Durduruldu", body="Kuyruk bitti veya bot kanaldan ayrıldı.", color=COLORS.DANGER)
