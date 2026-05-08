import sys
import pathlib
import pytest
from datetime import datetime, timezone, timedelta

# Ensure repo root is importable
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from cogs._v2 import COLORS, c_text, c_section, c_thumbnail, c_separator, c_container, c_media, c_badge, c_status_indicator, c_code_block, c_timestamp, c_rich_card, c_card, c_error, c_success, c_field, c_progress, c_kv_block, c_action_card, c_info_card, c_list_card
from cogs.moderation._shared import parse_duration, hierarchy_ok
from cogs.fun._shared import normalize_saat, parse_datetime, giphy, SEKIZ_TOP_YANIT, TÜRKÇE_AYLAR
from cogs.music._shared import duration_fmt, is_url, is_playlist_url, detect_platform, platform_label, Track, GuildPlayer

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_interaction():
    """Bare mock for hierarchy_ok tests that only reads guild/user attrs."""
    class FakeGuild:
        def __init__(self):
            self.me = None
            self.owner_id = 1
    class FakeUser:
        def __init__(self, uid, top_role=None):
            self.id = uid
            self.top_role = top_role or FakeRole(0)
    class FakeRole:
        def __init__(self, pos):
            self.position = pos
        def __ge__(self, other):
            return self.position >= other.position
        def __le__(self, other):
            return self.position <= other.position
    class FakeInteraction:
        def __init__(self, user=None, guild=None):
            self.user = user
            self.guild = guild
    return FakeInteraction, FakeUser, FakeGuild, FakeRole

@pytest.fixture
def fixed_now():
    return datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc)
