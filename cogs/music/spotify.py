"""Spotify URL'lerinden metadata çekme. Audio streaming değil — Spotify
DRM nedeniyle direkt indirilemez, biz sadece (artist, title) çıkarıyoruz
ve sonra YouTube'da arıyoruz.

Çalışması için ortam değişkenleri:
- SPOTIFY_CLIENT_ID
- SPOTIFY_CLIENT_SECRET

Spotify Developer Dashboard'dan ücretsiz alınır: https://developer.spotify.com/
"""
from __future__ import annotations

import os
import re
import asyncio

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    _HAS_SPOTIPY = True
except ImportError:
    spotipy = None
    SpotifyClientCredentials = None
    _HAS_SPOTIPY = False


_SPOTIFY_HOST_RE     = re.compile(r"open\.spotify\.com")
_SPOTIFY_TRACK_RE    = re.compile(r"open\.spotify\.com/(?:intl-\w+/)?track/([a-zA-Z0-9]+)")
_SPOTIFY_ALBUM_RE    = re.compile(r"open\.spotify\.com/(?:intl-\w+/)?album/([a-zA-Z0-9]+)")
_SPOTIFY_PLAYLIST_RE = re.compile(r"open\.spotify\.com/(?:intl-\w+/)?playlist/([a-zA-Z0-9]+)")

# 100 üzerinde olabilen Spotify playlistleri için sınır
_PLAYLIST_LIMIT = 100

_client = None  # lazy init


def is_spotify_url(url: str) -> bool:
    return bool(_SPOTIFY_HOST_RE.search(url))


def is_spotify_collection(url: str) -> bool:
    """Album veya playlist mi (yani çok şarkılı)."""
    return bool(_SPOTIFY_ALBUM_RE.search(url) or _SPOTIFY_PLAYLIST_RE.search(url))


def is_available() -> bool:
    """Spotify entegrasyonu yapılandırıldı mı?"""
    if not _HAS_SPOTIPY:
        return False
    return bool(os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET"))


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not is_available():
        return None
    auth = SpotifyClientCredentials(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    )
    _client = spotipy.Spotify(auth_manager=auth, requests_timeout=10, retries=2)
    return _client


def _track_to_query(track: dict) -> tuple[str, str] | None:
    if not track:
        return None
    artists = ", ".join(a.get("name", "") for a in track.get("artists", []) if a)
    title = track.get("name", "")
    if not title:
        return None
    return (artists.strip(), title.strip())


async def fetch_spotify_tracks(url: str) -> list[tuple[str, str]]:
    """Spotify URL'den (artist, title) çiftleri döner.

    - Track URL → 1 öğe
    - Album URL → albümdeki tüm şarkılar
    - Playlist URL → playlist'teki şarkılar (max 100)

    Hata durumunda boş liste.
    """
    client = _get_client()
    if client is None:
        return []

    loop = asyncio.get_running_loop()

    # Single track
    if m := _SPOTIFY_TRACK_RE.search(url):
        try:
            track = await loop.run_in_executor(None, client.track, m.group(1))
            q = _track_to_query(track)
            return [q] if q else []
        except Exception as e:
            print(f"[spotify] track fetch hatası: {e}")
            return []

    # Album
    if m := _SPOTIFY_ALBUM_RE.search(url):
        try:
            album = await loop.run_in_executor(None, client.album, m.group(1))
            tracks = album.get("tracks", {}).get("items", [])
            queries: list[tuple[str, str]] = []
            for t in tracks[:_PLAYLIST_LIMIT]:
                q = _track_to_query(t)
                if q:
                    queries.append(q)
            return queries
        except Exception as e:
            print(f"[spotify] album fetch hatası: {e}")
            return []

    # Playlist
    if m := _SPOTIFY_PLAYLIST_RE.search(url):
        try:
            playlist_id = m.group(1)
            queries: list[tuple[str, str]] = []
            offset = 0
            while len(queries) < _PLAYLIST_LIMIT:
                results = await loop.run_in_executor(
                    None,
                    lambda: client.playlist_items(
                        playlist_id, limit=50, offset=offset,
                        fields="items(track(name,artists(name))),next",
                    ),
                )
                items = results.get("items") or []
                if not items:
                    break
                for item in items:
                    track = item.get("track")
                    q = _track_to_query(track) if track else None
                    if q:
                        queries.append(q)
                if not results.get("next"):
                    break
                offset += 50
            return queries[:_PLAYLIST_LIMIT]
        except Exception as e:
            print(f"[spotify] playlist fetch hatası: {e}")
            return []

    return []


def format_query(artist: str, title: str) -> str:
    """YouTube araması için sorgu metni."""
    if artist:
        return f"{artist} - {title}"
    return title


# ── Extension entry-point (required by discord.py) ────────────────────────────

async def setup(bot: commands.Bot):
    """Helper module — no cog to load, but required for extension discovery."""
    pass
