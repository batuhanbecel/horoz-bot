import pytest
from cogs.moderation._shared import parse_duration, hierarchy_ok

# ── parse_duration ──────────────────────────────────────────────────────────────

class TestParseDuration:
    def test_seconds(self):
        td = parse_duration("30s")
        assert td.total_seconds() == 30

    def test_minutes(self):
        td = parse_duration("10m")
        assert td.total_seconds() == 600

    def test_hours(self):
        td = parse_duration("2h")
        assert td.total_seconds() == 7200

    def test_days(self):
        td = parse_duration("3d")
        assert td.total_seconds() == 259200

    def test_invalid(self):
        assert parse_duration("abc") is None
        assert parse_duration("10x") is None
        assert parse_duration("") is None

    def test_large_days(self):
        td = parse_duration("1000d")
        assert td is not None
        assert td.total_seconds() == 86400000

# ── hierarchy_ok ──────────────────────────────────────────────────────────────────

class TestHierarchyOk:
    def test_none_guild(self, mock_interaction):
        FI, FU, _, _ = mock_interaction
        ia = FI(user=None, guild=None)
        assert hierarchy_ok(ia, None) == "Bu komut sadece sunucuda çalışır."

    def test_self_target(self, mock_interaction):
        FI, FU, FG, FR = mock_interaction
        guild = FG()
        user = FU(5)
        guild.me = FU(99)
        ia = FI(user=user, guild=guild)
        assert hierarchy_ok(ia, user) == "Kendinize bu işlemi yapamazsınız."

    def test_bot_target(self, mock_interaction):
        FI, FU, FG, FR = mock_interaction
        guild = FG()
        bot = FU(99)
        guild.me = bot
        user = FU(5)
        ia = FI(user=user, guild=guild)
        assert hierarchy_ok(ia, bot) == "Bana bu işlemi yapamazsınız. 🐓"

    def test_owner_target(self, mock_interaction):
        FI, FU, FG, FR = mock_interaction
        guild = FG()
        guild.owner_id = 1
        guild.me = FU(99)
        owner = FU(1)
        user = FU(5)
        ia = FI(user=user, guild=guild)
        assert hierarchy_ok(ia, owner) == "Sunucu sahibine bu işlem yapılamaz."

    def test_equal_roles_skipped_because_not_member_instance(self, mock_interaction):
        # hierarchy_ok checks isinstance(interaction.user, discord.Member).
        # Our simple mock is not a real Member, so this branch is skipped.
        # This is a known test limitation; the branch is covered by integration tests.
        FI, FU, FG, FR = mock_interaction
        guild = FG()
        guild.owner_id = 1
        guild.me = FU(99, top_role=FR(10))
        target = FU(5, top_role=FR(5))
        user = FU(2, top_role=FR(5))
        ia = FI(user=user, guild=guild)
        # Since FakeUser is not discord.Member, the user-role check is skipped.
        # Bot-role check: FR(5) >= FR(10) is False → returns None (OK)
        assert hierarchy_ok(ia, target) is None

    def test_bot_role_lower(self, mock_interaction):
        FI, FU, FG, FR = mock_interaction
        guild = FG()
        guild.owner_id = 1
        guild.me = FU(99, top_role=FR(3))
        target = FU(5, top_role=FR(5))
        user = FU(2, top_role=FR(10))
        ia = FI(user=user, guild=guild)
        assert hierarchy_ok(ia, target) == "Bu üyenin rolü botun rolünden yüksek veya eşit."

    def test_owner_bypass(self, mock_interaction):
        FI, FU, FG, FR = mock_interaction
        guild = FG()
        guild.owner_id = 1
        guild.me = FU(99, top_role=FR(10))
        target = FU(5, top_role=FR(5))
        owner = FU(1, top_role=FR(0))
        ia = FI(user=owner, guild=guild)
        assert hierarchy_ok(ia, target) is None

    def test_ok(self, mock_interaction):
        FI, FU, FG, FR = mock_interaction
        guild = FG()
        guild.owner_id = 1
        guild.me = FU(99, top_role=FR(10))
        target = FU(5, top_role=FR(3))
        user = FU(2, top_role=FR(5))
        ia = FI(user=user, guild=guild)
        assert hierarchy_ok(ia, target) is None
