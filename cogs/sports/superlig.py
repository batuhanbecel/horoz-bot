"""
cogs/sports/superlig.py — Trendyol Süper Lig komutları
API: api-football.com (ücretsiz tier: 100 istek/gün)
Env: FOOTBALL_API_KEY
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import (
    COLORS,
    c_card,
    c_container,
    c_separator,
    c_text,
    edit_original,
    error_response,
    respond,
)

log = logging.getLogger("horoz_bot.superlig")

LEAGUE_ID = 203          # Trendyol Süper Lig
API_BASE  = "https://v3.football.api-sports.io"

RANK_EMOJI  = {1: "🥇", 2: "🥈", 3: "🥉"}
FORM_EMOJI  = {"W": "🟩", "D": "🟨", "L": "🟥"}

# Rank → zone emoji (18 takımlı lig, 3 küme düşer)
ZONES: dict[int, str] = {1: "🔵", 2: "🔵", 3: "🔵", 4: "🟠", 5: "🟠", 6: "🟢"}
RELEGATION_FROM = 16


def _current_season() -> int:
    now = datetime.now(timezone.utc)
    return now.year if now.month >= 7 else now.year - 1


def _zone(rank: int) -> str:
    if rank >= RELEGATION_FROM:
        return "🔴"
    return ZONES.get(rank, "⬛")


def _form(raw: str) -> str:
    return "".join(FORM_EMOJI.get(c, "⬛") for c in raw[-5:])


def _round_label(api_round: str) -> str:
    return api_round.replace("Regular Season - ", "Hafta ")


# Loading card — ping komutundaki gibi önce bu gönderilir, sonra edit_original
def _loading() -> dict:
    return c_card(
        "## 🏆 Trendyol Süper Lig",
        body="`─────────────────` Yükleniyor...",
        color=0xE32429,
    )


class SuperLig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._key  = os.getenv("FOOTBALL_API_KEY", "")
        self._cache: dict[str, tuple[dict, float]] = {}

    # ── API helpers ────────────────────────────────────────────────────────────

    async def _fetch(self, endpoint: str, params: dict, *, ttl: int = 300) -> dict | None:
        """API isteği yapar. HTTP 200 dışındaki cevapları da döner (hata detayı için)."""
        if not self._key:
            return None
        cache_key = f"{endpoint}:{sorted(params.items())}"
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if time.time() - ts < ttl:
                return data
        headers = {"x-apisports-key": self._key}
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as s:
                async with s.get(f"{API_BASE}/{endpoint}", params=params) as r:
                    data = await r.json(content_type=None)
                    if r.status == 200:
                        self._cache[cache_key] = (data, time.time())
                    else:
                        log.warning("API %s %s → HTTP %d: %s", endpoint, params, r.status, data)
                    return data
        except Exception as exc:
            log.error("API fetch error (%s %s): %s", endpoint, params, exc)
        return None

    def _api_error_msg(self, data: dict | None) -> str:
        if data is None:
            return "API'ye ulaşılamadı (timeout veya ağ hatası)."
        errors = data.get("errors")
        if isinstance(errors, dict) and errors:
            return "API hatası: " + " · ".join(f"`{k}: {v}`" for k, v in errors.items())
        if isinstance(errors, list) and errors:
            return "API hatası: " + str(errors[0])
        return f"Sezon veya lig için veri bulunamadı. (results: {data.get('results', '?')})"

    def _error_card(self, msg: str) -> dict:
        return c_container(
            c_text("## ❌ Hata"),
            c_separator(),
            c_text(msg),
            color=COLORS.DANGER,
        )

    def _no_key_card(self) -> dict:
        return c_container(
            c_text("## ❌ API Anahtarı Eksik"),
            c_separator(),
            c_text(
                "`.env` dosyasına `FOOTBALL_API_KEY` eklemen gerekiyor.\n\n"
                "Ücretsiz (100 istek/gün): **api-football.com** → Register → API Key"
            ),
            color=COLORS.DANGER,
        )

    # ── Command group ──────────────────────────────────────────────────────────

    lig = app_commands.Group(
        name="lig",
        description="🏆 Trendyol Süper Lig komutları",
    )

    # /lig sıralama ─────────────────────────────────────────────────────────────

    @lig.command(name="sıralama", description="Süper Lig puan tablosunu gösterir.")
    async def siralama(self, interaction: discord.Interaction):
        # Ping patterni: önce loading kartı gönder (type-4 V2), sonra edit_original
        await respond(interaction, _loading())

        if not self._key:
            await edit_original(interaction, self._no_key_card())
            return

        season = _current_season()
        data = await self._fetch("standings", {"league": LEAGUE_ID, "season": season})

        if not data or not data.get("response"):
            await edit_original(interaction, self._error_card(self._api_error_msg(data)))
            return

        try:
            standings = data["response"][0]["league"]["standings"][0]
        except (KeyError, IndexError) as exc:
            await edit_original(interaction, self._error_card(f"Puan tablosu ayrıştırılamadı: `{exc}`"))
            return

        rows: list[str] = []
        for team in standings:
            rank     = team["rank"]
            name     = team["team"]["name"]
            pts      = team["points"]
            played   = team["all"]["played"]
            w        = team["all"]["win"]
            d        = team["all"]["draw"]
            l        = team["all"]["lose"]
            gf       = team["all"]["goals"]["for"] or 0
            ga       = team["all"]["goals"]["against"] or 0
            diff     = gf - ga
            form_raw = (team.get("form") or "")
            form     = _form(form_raw) if form_raw else "─ ─ ─ ─ ─"

            rank_str = RANK_EMOJI.get(rank, f"`{rank:2d}.`")
            zone     = _zone(rank)
            diff_str = f"+{diff}" if diff >= 0 else str(diff)

            rows.append(
                f"{rank_str} {zone} **{name}** — **{pts}P**"
                f" · O:{played} G:{w} B:{d} M:{l} · {gf}:{ga} ({diff_str})\n"
                f"-# {form}"
            )

        mid      = (len(rows) + 1) // 2
        top_text = "\n\n".join(rows[:mid])
        bot_text = "\n\n".join(rows[mid:])

        await edit_original(
            interaction,
            c_container(
                c_text(
                    f"## 🏆 Trendyol Süper Lig — Puan Tablosu\n"
                    f"-# {season}–{season + 1} Sezonu"
                ),
                c_separator(),
                c_text(top_text),
                c_separator(),
                c_text(bot_text),
                c_separator(),
                c_text(
                    "-# 🔵 Şampiyonlar Ligi · 🟠 Avrupa Ligi · 🟢 Konferans Ligi · 🔴 Küme Düşme"
                ),
                color=0xE32429,
            ),
        )

    # /lig takvim ───────────────────────────────────────────────────────────────

    @lig.command(name="takvim", description="Yaklaşan Süper Lig maçlarını gösterir.")
    async def takvim(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        if not self._key:
            await edit_original(interaction, self._no_key_card())
            return

        season = _current_season()
        # `next=N` parametresi otomatik olarak oynamanmış (NS) maçları döner —
        # from/to/status kombinasyonu bazı plan seviyelerinde desteklenmez.
        data = await self._fetch(
            "fixtures",
            {"league": LEAGUE_ID, "season": season, "next": 10},
        )

        if not data:
            await edit_original(interaction, self._error_card(self._api_error_msg(data)))
            return

        fixtures = data.get("response", [])
        if not fixtures:
            await edit_original(
                interaction,
                c_container(
                    c_text("## 📅 Maç Takvimi"),
                    c_separator(),
                    c_text("Yaklaşan maç bulunamadı. Sezon tamamlanmış olabilir."),
                    color=COLORS.INFO,
                ),
            )
            return

        rounds: dict[str, list[str]] = {}
        for fix in fixtures:
            rnd  = fix["league"]["round"]
            dt   = datetime.fromisoformat(fix["fixture"]["date"].replace("Z", "+00:00"))
            ts   = int(dt.timestamp())
            home = fix["teams"]["home"]["name"]
            away = fix["teams"]["away"]["name"]
            row  = f"📅 <t:{ts}:d> <t:{ts}:t> · **{home}** 🆚 **{away}**"
            rounds.setdefault(rnd, []).append(row)

        sections = [
            f"**📌 {_round_label(rnd)}**\n" + "\n".join(matches)
            for rnd, matches in rounds.items()
        ]

        await edit_original(
            interaction,
            c_container(
                c_text(
                    f"## 📅 Trendyol Süper Lig — Maç Takvimi\n"
                    f"-# {season}–{season + 1} Sezonu · Sonraki {len(fixtures)} maç"
                ),
                c_separator(),
                c_text("\n\n".join(sections)),
                c_separator(),
                c_text("-# Saatler yerel saat diliminize göre gösterilir"),
                color=COLORS.INFO,
            ),
        )

    # /lig sonuçlar ─────────────────────────────────────────────────────────────

    @lig.command(name="sonuçlar", description="Son Süper Lig maç sonuçlarını gösterir.")
    async def sonuclar(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        if not self._key:
            await edit_original(interaction, self._no_key_card())
            return

        season = _current_season()
        data = await self._fetch(
            "fixtures",
            {"league": LEAGUE_ID, "season": season, "last": 15},
        )

        if not data:
            await edit_original(interaction, self._error_card(self._api_error_msg(data)))
            return

        fixtures = list(reversed(data.get("response", [])))
        if not fixtures:
            await edit_original(
                interaction,
                c_container(
                    c_text("## 📊 Son Sonuçlar"),
                    c_separator(),
                    c_text("Henüz tamamlanmış maç bulunamadı."),
                    color=COLORS.INFO,
                ),
            )
            return

        rounds: dict[str, list[str]] = {}
        for fix in fixtures:
            rnd      = fix["league"]["round"]
            dt       = datetime.fromisoformat(fix["fixture"]["date"].replace("Z", "+00:00"))
            ts       = int(dt.timestamp())
            home     = fix["teams"]["home"]["name"]
            away     = fix["teams"]["away"]["name"]
            gh       = fix["goals"]["home"] or 0
            ga       = fix["goals"]["away"] or 0
            home_win = fix["teams"]["home"].get("winner")
            away_win = fix["teams"]["away"].get("winner")

            if home_win:
                row = f"🟩 <t:{ts}:d> · **{home} {gh}–{ga}** {away}"
            elif away_win:
                row = f"🟩 <t:{ts}:d> · {home} **{gh}–{ga} {away}**"
            else:
                row = f"🟨 <t:{ts}:d> · {home} {gh}–{ga} {away}"

            rounds.setdefault(rnd, []).append(row)

        sections = [
            f"**📌 {_round_label(rnd)}**\n" + "\n".join(matches)
            for rnd, matches in rounds.items()
        ]

        await edit_original(
            interaction,
            c_container(
                c_text(
                    f"## 📊 Trendyol Süper Lig — Son Sonuçlar\n"
                    f"-# {season}–{season + 1} Sezonu"
                ),
                c_separator(),
                c_text("\n\n".join(sections)),
                c_separator(),
                c_text("-# 🟩 Kazanan kalın · 🟨 Beraberlik"),
                color=COLORS.SUCCESS,
            ),
        )

    # /lig canlı ────────────────────────────────────────────────────────────────

    @lig.command(name="canlı", description="Devam eden Süper Lig maçlarının canlı skorlarını gösterir.")
    async def canli(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        if not self._key:
            await edit_original(interaction, self._no_key_card())
            return

        data = await self._fetch(
            "fixtures",
            {"league": LEAGUE_ID, "live": "all"},
            ttl=60,
        )

        if not data:
            await edit_original(interaction, self._error_card(self._api_error_msg(data)))
            return

        fixtures = data.get("response", [])
        if not fixtures:
            await edit_original(
                interaction,
                c_container(
                    c_text("## 🔴 Canlı Maçlar"),
                    c_separator(),
                    c_text("Şu an devam eden Süper Lig maçı yok."),
                    color=COLORS.NEUTRAL,
                ),
            )
            return

        rows: list[str] = []
        for fix in fixtures:
            home    = fix["teams"]["home"]["name"]
            away    = fix["teams"]["away"]["name"]
            gh      = fix["goals"]["home"] or 0
            ga      = fix["goals"]["away"] or 0
            elapsed = fix["fixture"]["status"].get("elapsed") or "?"
            rows.append(f"🔴 **{elapsed}'** · **{home} {gh}–{ga} {away}**")

        await edit_original(
            interaction,
            c_container(
                c_text("## 🔴 Canlı Maçlar — Trendyol Süper Lig"),
                c_separator(),
                c_text("\n".join(rows)),
                c_separator(),
                c_text("-# Canlı skorlar · Komut tekrarlanarak yenilenir"),
                color=0xFF0000,
            ),
        )

    # ── Error handler ──────────────────────────────────────────────────────────

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        log.error("Lig komutu hatası: %s", error)
        await error_response(interaction, str(error))


async def setup(bot: commands.Bot):
    await bot.add_cog(SuperLig(bot))
