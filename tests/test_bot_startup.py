import pytest
import sys
import pathlib
from datetime import datetime, timezone

# ── startup smoke tests ────────────────────────────────────────────────────────

class TestBotImports:
    def test_import_main(self):
        import main
        assert hasattr(main, "HorozBot")

    def test_import_v2(self):
        from cogs._v2 import COLORS, c_card
        assert COLORS.PRIMARY == 0x5865F2

    def test_import_error_handler(self):
        from cogs import error_handler
        assert hasattr(error_handler, "ErrorHandler")

    def test_import_moderation_member(self):
        from cogs.moderation import member as mod_member
        assert hasattr(mod_member, "MemberMod")

    def test_import_utility_info(self):
        from cogs.utility import info as util_info
        assert hasattr(util_info, "Info")

    def test_import_music_player(self):
        from cogs.music import player as music_player
        assert hasattr(music_player, "Music")

    def test_import_fun_social(self):
        from cogs.fun import social as fun_social
        assert hasattr(fun_social, "Social")

    def test_cog_discovery(self):
        import main
        cogs = main.discover_cogs()
        assert isinstance(cogs, list)
        # core cogs should be discovered
        assert any("error_handler" in c for c in cogs)
        assert any("moderation.member" in c for c in cogs)
        assert any("fun.games" in c for c in cogs)
        assert any("music.player" in c for c in cogs)
        assert any("utility.info" in c for c in cogs)

    def test_cog_has_setup(self):
        import importlib
        cogs = [
            "cogs.error_handler",
            "cogs.moderation.member",
            "cogs.utility.info",
            "cogs.music.player",
            "cogs.music.lyrics",
            "cogs.music.spotify",
            "cogs.fun.social",
            "cogs.fun.games",
            "cogs.fun.vampir_koylu",
            "cogs.fun.arena",
        ]
        for cog in cogs:
            mod = importlib.import_module(cog)
            assert hasattr(mod, "setup"), f"{cog} missing setup()"

    def test_import_no_syntax_errors(self):
        import py_compile
        base = pathlib.Path(__file__).resolve().parent.parent / "cogs"
        for py in base.rglob("*.py"):
            if py.name.startswith("_"):
                continue
            py_compile.compile(str(py), doraise=True)

# ── error handler specific ─────────────────────────────────────────────────────

class TestErrorHandler:
    def test_error_handler_maps_errors(self):
        from cogs.error_handler import ErrorHandler
        # Just verify it can be constructed with a dummy bot
        class DummyBot:
            pass
        cog = ErrorHandler(DummyBot())
        assert cog is not None
