import pytest
import sys
from collections import deque

# ── music shared helpers ────────────────────────────────────────────────────────

class TestDurationFmt:
    def test_zero(self):
        from cogs.music._shared import duration_fmt
        assert duration_fmt(0) == "?"

    def test_seconds(self):
        from cogs.music._shared import duration_fmt
        assert duration_fmt(45) == "00:45"

    def test_minutes(self):
        from cogs.music._shared import duration_fmt
        assert duration_fmt(125) == "02:05"

    def test_hours(self):
        from cogs.music._shared import duration_fmt
        assert duration_fmt(3665) == "01:01:05"


class TestIsUrl:
    def test_http(self):
        from cogs.music._shared import is_url
        assert is_url("http://example.com")

    def test_https(self):
        from cogs.music._shared import is_url
        assert is_url("https://example.com")

    def test_plain(self):
        from cogs.music._shared import is_url
        assert not is_url("hello world")


class TestIsPlaylistUrl:
    def test_list_param(self):
        from cogs.music._shared import is_playlist_url
        assert is_playlist_url("https://youtube.com/playlist?list=abc")

    def test_path(self):
        from cogs.music._shared import is_playlist_url
        assert is_playlist_url("https://youtube.com/playlist/abc")

    def test_not_playlist(self):
        from cogs.music._shared import is_playlist_url
        assert not is_playlist_url("https://youtube.com/watch?v=abc")


class TestDetectPlatform:
    def test_spotify(self):
        from cogs.music._shared import detect_platform
        assert detect_platform("https://open.spotify.com/track/123") == "spotify"

    def test_youtube(self):
        from cogs.music._shared import detect_platform
        assert detect_platform("https://youtube.com/watch?v=123") == "youtube"
        assert detect_platform("https://youtu.be/123") == "youtube"

    def test_soundcloud(self):
        from cogs.music._shared import detect_platform
        assert detect_platform("https://soundcloud.com/artist/song") == "soundcloud"

    def test_other(self):
        from cogs.music._shared import detect_platform
        assert detect_platform("https://example.com") == "other"

    def test_empty(self):
        from cogs.music._shared import detect_platform
        assert detect_platform("") == "other"


class TestPlatformLabel:
    def test_known(self):
        from cogs.music._shared import platform_label
        assert "YouTube" in platform_label("youtube")
        assert "Spotify" in platform_label("spotify")

    def test_unknown(self):
        from cogs.music._shared import platform_label
        assert "Diğer" in platform_label("unknown")


class TestYtThumbnail:
    def test_watch_url(self):
        from cogs.music._shared import yt_thumbnail
        assert yt_thumbnail("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"

    def test_short_url(self):
        from cogs.music._shared import yt_thumbnail
        assert yt_thumbnail("https://youtu.be/dQw4w9WgXcQ") == "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"

    def test_no_match(self):
        from cogs.music._shared import yt_thumbnail
        assert yt_thumbnail("https://example.com") is None


class TestTrackDefaults:
    def test_track_dataclass_defaults(self):
        from cogs.music._shared import Track
        # requester is required, but since it's a dataclass we can still inspect fields
        assert Track.__dataclass_fields__["duration"].default == 0
        assert Track.__dataclass_fields__["stream_url"].default is None
        assert Track.__dataclass_fields__["platform"].default == "youtube"
        assert Track.__dataclass_fields__["source_url"].default is None


class TestGuildPlayerDefaults:
    def test_defaults(self):
        from cogs.music._shared import GuildPlayer
        # Cannot instantiate without discord Member, but verify defaults from definition
        assert GuildPlayer.__dataclass_fields__["volume"].default == 0.5
        assert GuildPlayer.__dataclass_fields__["loop"].default == False
        assert GuildPlayer.__dataclass_fields__["paused"].default == False
