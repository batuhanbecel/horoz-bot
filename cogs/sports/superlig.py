"""
cogs/sports/superlig.py — Trendyol Süper Lig komutları
API: api-football.com (ücretsiz tier: 100 istek/gün)
Env: FOOTBALL_API_KEY
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import (
    COLORS,
    c_container,
    c_separator,
    c_text,
    edit_original,
    error_response,
    respond,
)

LEAGUE_ID = 203          # Trendyol Süper Lig
API_BASE  = "https://v3.football.api-sports.io"

RANK_EMOJI  = {1: "🥇", 2: "🥈", 3: "🥉"}
FORM_EMOJI  = {"W": "🟩", "D": "🟨", "L": "🟥"}

# Rank → (zone emoji, zone label)  — 18 takımlı lig
ZONES: dict[int, tuple[str, str]] = {
    1: ("🔵", "Şampiyonlar Ligi"),
    2: ("🔵", "Şampiyonlar Ligi (E)"),
    3: ("🔵", "Şampiyonlar Ligi (E)"),
    4: ("🟠", "Avrupa Ligi"),
    5: ("🟠", "Avrupa Ligi (E)"),
    6: ("🟢", "Konferans Ligi"),
}
RELEGATION_FROM = 16  # 16, 17, 18 → küme düşme


def _current_season() -> int:
    now = datetime.now(timezone.utc)
    return now.year if now.month >= 7 else now.year - 1


def _zone(rank: int) -> str:
    if rank >= RELEGATION_FROM:
        return "🔴"
    return ZONES.get(rank, ("⬛", ""))[0]


def _form(raw: str) -> str:
    return "".join(FORM_EMOJI.get(c, "⬛") for c in raw[-5:])


def _round_label(api_round: str) -> str:
    return api_round.replace("Regular Season - ", "Hafta ")


class SuperLig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._key  = os.getenv("FOOTBALL_API_KEY", "")
        self._cache: dict[str, tuple[dict, float]] = {}

    # ── API helpers ────────────────────────────────────────────────────────────

    async def _fetch(
        self, endpoint: str, params: dict, *, ttl: int = 300
    ) -> dict | None:
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
                    if r.status == 200:
                        data = await r.json()
                        self._cache[cache_key] = (data, time.time())
                        return data
        except Exception:
            pass
        return None

    def _no_key_card(self) -> dict:
        return c_container(
            c_text("## ❌ API Anahtarı Eksik"),
            c_separator(),
            c_text(
                "`.env` dosyasına `FOOTBALL_API_KEY` eklemen gerekiyor.\n\n"
                "Ücretsiz (100 istek/gün) almak için:\n"
                "**[api-football.com](https://www.api-football.com/)** → Register → API Key"
            ),
            color=COLORS.DANGER,
        )

    def _error_card(self, msg: str = "Veri alınamadı. Lütfen daha sonra tekrar dene.") -> dict:
        return c_container(
            c_text("## ❌ Hata"),
            c_separator(),
            c_text(msg),
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
        await interaction.response.defer()

        if not self._key:
            await edit_original(interaction, self._no_key_card())
            return

        season = _current_season()
        data = await self._fetch(
            "standings", {"league": LEAGUE_ID, "season": season}
        )

        if not data or not data.get("response"):
            await edit_original(interaction, self._error_card())
            return

        try:
            standings = data["response"][0]["league"]["standings"][0]
        except (KeyError, IndexError):
            await edit_original(interaction, self._error_card("Puan tablosu verisi okunamadı."))
            return

        rows: list[str] = []
        for team in standings:
            rank  = team["rank"]
            name  = team["team"]["name"]
            pts   = team["points"]
            played = team["all"]["played"]
            w     = team["all"]["win"]
            d     = team["all"]["draw"]
            l     = team["all"]["lose"]
            gf    = team["all"]["goals"]["for"]
            ga    = team["all"]["goals"]["against"]
            diff  = gf - ga
            form_raw = (team.get("form") or "")
            form  = _form(form_raw) if form_raw else "─ ─ ─ ─ ─"

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
        await interaction.response.defer()

        if not self._key:
            await edit_original(interaction, self._no_key_card())
            return

        season  = _current_season()
        today   = datetime.now(timezone.utc)
        from_dt = today.strftime("%Y-%m-%d")
        to_dt   = (today + timedelta(days=30)).strftime("%Y-%m-%d")

        data = await self._fetch(
            "fixtures",
            {"league": LEAGUE_ID, "season": season, "from": from_dt, "to": to_dt, "status": "NS"},
        )

        if not data or not data.get("response"):
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

        fixtures = data["response"][:15]
        rounds: dict[str, list[str]] = {}

        for fix in fixtures:
            rnd     = fix["league"]["round"]
            dt      = datetime.fromisoformat(fix["fixture"]["date"].replace("Z", "+00:00"))
            ts      = int(dt.timestamp())
            home    = fix["teams"]["home"]["name"]
            away    = fix["teams"]["away"]["name"]
            row     = f"📅 <t:{ts}:d> <t:{ts}:t> · **{home}** 🆚 **{away}**"
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
                    f"-# {season}–{season + 1} Sezonu · Önümüzdeki 30 gün"
                ),
                c_separator(),
                c_text("\n\n".join(sections) if sections else "Yaklaşan maç yok."),
                c_separator(),
                c_text("-# Saatler yerel saat diliminize göre gösterilir"),
                color=COLORS.INFO,
            ),
        )

    # /lig sonuçlar ─────────────────────────────────────────────────────────────

    @lig.command(name="sonuçlar", description="Son Süper Lig maç sonuçlarını gösterir.")
    async def sonuclar(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not self._key:
            await edit_original(interaction, self._no_key_card())
            return

        season = _current_season()
        data = await self._fetch(
            "fixtures",
            {"league": LEAGUE_ID, "season": season, "last": 15, "status": "FT"},
        )

        if not data or not data.get("response"):
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

        fixtures = list(reversed(data["response"]))
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
                c_text("\n\n".join(sections) if sections else "Sonuç bulunamadı."),
                c_separator(),
                c_text("-# 🟩 Kazanan kalın · 🟨 Beraberlik"),
                color=COLORS.SUCCESS,
            ),
        )

    # /lig canlı ────────────────────────────────────────────────────────────────

    @lig.command(name="canlı", description="Devam eden Süper Lig maçlarının canlı skorlarını gösterir.")
    async def canli(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not self._key:
            await edit_original(interaction, self._no_key_card())
            return

        data = await self._fetch(
            "fixtures",
            {"league": LEAGUE_ID, "live": "all"},
            ttl=60,
        )

        if not data or not data.get("response"):
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
        for fix in data["response"]:
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
        await error_response(interaction, str(error))


async def setup(bot: commands.Bot):
    await bot.add_cog(SuperLig(bot))
