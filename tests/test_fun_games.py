import pytest
from datetime import datetime, timezone, timedelta

# ── pure helpers from fun/_shared ───────────────────────────────────────────────

class TestNormalizeSaat:
    def test_dot_to_colon(self):
        from cogs.fun._shared import normalize_saat
        assert normalize_saat("20.00") == "20:00"

    def test_four_digits(self):
        from cogs.fun._shared import normalize_saat
        assert normalize_saat("2000") == "20:00"

    def test_colon_unchanged(self):
        from cogs.fun._shared import normalize_saat
        assert normalize_saat("20:00") == "20:00"


class TestParseDatetime:
    def test_dd_mm_yyyy(self):
        from cogs.fun._shared import parse_datetime
        dt = parse_datetime("25.05.2026", "20:00")
        assert dt == datetime(2026, 5, 25, 20, 0, tzinfo=timezone.utc)

    def test_turkish_month(self):
        from cogs.fun._shared import parse_datetime
        dt = parse_datetime("25 Mayıs 2026", "20:00")
        assert dt == datetime(2026, 5, 25, 20, 0, tzinfo=timezone.utc)

    def test_invalid(self):
        from cogs.fun._shared import parse_datetime
        assert parse_datetime("abc", "20:00") is None


# ── TKM helpers ─────────────────────────────────────────────────────────────────

class TestTkmTur:
    def test_berabere(self):
        from cogs.fun.games import _tkm_tur
        assert _tkm_tur("taş", "taş") == "berabere"

    def test_1_wins(self):
        from cogs.fun.games import _tkm_tur
        assert _tkm_tur("taş", "makas") == "1"
        assert _tkm_tur("kağıt", "taş") == "1"
        assert _tkm_tur("makas", "kağıt") == "1"

    def test_2_wins(self):
        from cogs.fun.games import _tkm_tur
        assert _tkm_tur("makas", "taş") == "2"
        assert _tkm_tur("taş", "kağıt") == "2"
        assert _tkm_tur("kağıt", "makas") == "2"


# ── 8ball constants ───────────────────────────────────────────────────────────

class TestSekizTop:
    def test_list_not_empty(self):
        from cogs.fun._shared import SEKIZ_TOP_YANIT
        assert len(SEKIZ_TOP_YANIT) == 20

    def test_unique(self):
        from cogs.fun._shared import SEKIZ_TOP_YANIT
        assert len(set(SEKIZ_TOP_YANIT)) == len(SEKIZ_TOP_YANIT)


# ── adam asmaca TR norm ───────────────────────────────────────────────────────

class TestTrNorm:
    def test_mappings(self):
        from cogs.fun.games import _TR_NORM
        assert _TR_NORM["I"] == "İ"
        assert _TR_NORM["İ"] == "I"
        assert _TR_NORM["ı"] == "i"
        assert _TR_NORM["i"] == "ı"


# ── vampir_koylu role distribution ────────────────────────────────────────────

class TestRolDagit:
    def test_4_players(self):
        from cogs.fun.vampir_koylu import _rol_dagit
        assert _rol_dagit(4) == ["vampir", "köylü", "köylü", "köylü"]

    def test_8_players(self):
        from cogs.fun.vampir_koylu import _rol_dagit
        roles = _rol_dagit(8)
        assert len(roles) == 8
        assert roles.count("vampir") == 2

    def test_12_players(self):
        from cogs.fun.vampir_koylu import _rol_dagit
        roles = _rol_dagit(12)
        assert len(roles) == 12
        assert roles.count("vampir") == 3
        assert roles.count("avcı") == 1

    def test_invalid_large(self):
        from cogs.fun.vampir_koylu import _rol_dagit
        roles = _rol_dagit(20)
        assert len(roles) == 12  # max defined in function
