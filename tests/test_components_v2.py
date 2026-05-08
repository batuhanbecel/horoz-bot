import pytest
import discord
from cogs._v2 import (
    COLORS, c_text, c_section, c_thumbnail, c_separator, c_container, c_media,
    c_badge, c_status_indicator, c_code_block, c_timestamp,
    c_rich_card, c_card, c_error, c_success, c_field, c_progress, c_kv_block,
    c_action_card, c_info_card, c_list_card,
)

class TestColors:
    def test_colors_are_integers(self):
        for name, value in vars(COLORS).items():
            if not name.startswith("_"):
                assert isinstance(value, int), f"COLORS.{name} must be int"

    def test_colors_are_reasonable(self):
        for name, value in vars(COLORS).items():
            if not name.startswith("_"):
                assert 0 <= value <= 0xFFFFFF, f"COLORS.{name} out of 24-bit range"

    def test_colors_values(self):
        assert COLORS.PRIMARY == 0x5865F2
        assert COLORS.SUCCESS == 0x57F287
        assert COLORS.DANGER == 0xED4245

class TestBuilders:
    def test_c_text(self):
        td = c_text("hello")
        assert isinstance(td, discord.ui.TextDisplay)
        assert td.content == "hello"

    def test_c_thumbnail_with_url(self):
        th = c_thumbnail("http://a.jpg")
        assert isinstance(th, discord.ui.Thumbnail)
        assert th.media.url == "http://a.jpg"

    def test_c_thumbnail_none(self):
        assert c_thumbnail(None) is None
        assert c_thumbnail("") is None

    def test_c_separator_default(self):
        sep = c_separator()
        assert isinstance(sep, discord.ui.Separator)
        assert sep.to_component_dict()["type"] == 14
        assert sep.to_component_dict()["divider"] is True

    def test_c_separator_custom(self):
        sep = c_separator(4)
        assert isinstance(sep, discord.ui.Separator)

    def test_c_container_no_color(self):
        cont = c_container(c_text("a"))
        assert isinstance(cont, discord.ui.Container)
        assert cont.accent_color is None

    def test_c_container_with_color(self):
        cont = c_container(c_text("a"), color=0x123456)
        assert isinstance(cont, discord.ui.Container)
        assert cont.accent_color == 0x123456

    def test_c_media(self):
        mg = c_media("http://a.jpg", "http://b.jpg")
        assert isinstance(mg, discord.ui.MediaGallery)
        assert len(mg.items) == 2

    def test_c_badge(self):
        assert c_badge("test", "\U0001F7E2") == "`\U0001F7E2 test`"
        assert c_badge("test") == "`\U0001F535 test`"

    def test_c_status_indicator(self):
        assert c_status_indicator("ok") == "\U0001F7E2"
        assert c_status_indicator("warn", "text") == "\U0001F7E1 text"
        assert c_status_indicator("unknown") == "\U000026AA"

    def test_c_code_block(self):
        assert c_code_block("print(1)", "py") == "```py\nprint(1)\n```"

    def test_c_timestamp(self):
        assert c_timestamp(1715180000) == "<t:1715180000:F>"

    def test_c_field(self):
        assert c_field("Name", "Value") == "**Name:** Value"

    def test_c_progress(self):
        assert len(c_progress(5, 10, length=10)) == 10
        assert c_progress(0, 10, length=4) == "\u2500" * 4
        assert c_progress(10, 10, length=4) == "\u2501" * 4

    def test_c_kv_block(self):
        pairs = [("a", 1), ("b", "two")]
        assert c_kv_block(pairs) == "**a:** 1\n**b:** two"

class TestSection:
    def test_section_with_accessory(self):
        sec = c_section(c_text("header"), accessory=c_thumbnail("http://a.jpg"))
        assert isinstance(sec, discord.ui.Section)
        assert isinstance(sec.accessory, discord.ui.Thumbnail)

    def test_section_without_accessory_single(self):
        sec = c_section(c_text("only text"))
        assert isinstance(sec, discord.ui.TextDisplay)

    def test_section_without_accessory_multi(self):
        sec = c_section(c_text("a"), c_text("b"))
        assert isinstance(sec, discord.ui.TextDisplay)
        assert "a\nb" in sec.content

class TestCards:
    def test_c_card_basic(self):
        card = c_card("## Title", body="body")
        assert isinstance(card, discord.ui.Container)
        assert len(card.children) == 3

    def test_c_card_with_thumbnail(self):
        card = c_card("## Title", thumbnail="http://a.jpg")
        assert isinstance(card, discord.ui.Container)

    def test_c_error(self):
        err = c_error("oops")
        assert isinstance(err, discord.ui.Container)
        assert "oops" in str(err.to_components())

    def test_c_success(self):
        succ = c_success("ok")
        assert isinstance(succ, discord.ui.Container)
        assert "ok" in str(succ.to_components())

    def test_c_rich_card(self):
        card = c_rich_card(
            "Title",
            subtitle="Sub",
            body="Body",
            thumbnail="http://a.jpg",
            badges=[c_badge("A", "\U0001F7E2")],
            footer="foot",
            color=COLORS.PRIMARY,
        )
        assert isinstance(card, discord.ui.Container)
        assert card.accent_color == COLORS.PRIMARY

    def test_c_action_card(self):
        card = c_action_card("Action", target_avatar="http://a.jpg", fields=[("F", "V")])
        assert isinstance(card, discord.ui.Container)

    def test_c_info_card(self):
        card = c_info_card("Info", groups=[[("F", "V")]], media="http://a.jpg", footer="f")
        assert isinstance(card, discord.ui.Container)

    def test_c_list_card(self):
        card = c_list_card("List", rows=["a", "b"])
        assert isinstance(card, discord.ui.Container)
        assert len(card.children) == 3
