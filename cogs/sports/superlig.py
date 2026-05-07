"""
cogs/sports/superlig.py — Trendyol Süper Lig komutları
API: TheSportsDB (thesportsdb.com) — ücretsiz, key 123
"""
from __future__ import annotations

import json
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
    c_section,
    c_separator,
    c_text,
    c_thumbnail,
    edit_original,
    error_response,
    respond,
)

log = logging.getLogger("horoz_bot.superlig")

LEAGUE_ID = 4339   # Turkish Super Lig — thesportsdb.com
API_BASE  = "https://www.thesportsdb.com/api/v1/json/"
API_KEY   = os.getenv("THESPORTSDB_KEY", "123")

RANK_EMOJI = {1: "🥇", 2: "🥈", 3: "🥉"}

ZONE_MAP = {
    "champions league":  "🔵",
    "europa league":     "🟠",
    "conference league": "🟢",
    "relegation":        "🔴",
    "playoff":           "🔴",
}


def _zone(description: str) -> str:
    desc = (description or "").lower()
    for key, emoji in ZONE_MAP.items():
        if key in desc:
            return emoji
    return "⬛"


def _diff_str(val) -> str:
    try:
        v = int(val or 0)
        return f"+{v}" if v >= 0 else str(v)
    except (ValueError, TypeError):
        return str(val)


def _current_season() -> str:
    now = datetime.now(timezone.utc)
    if now.month >= 7:
        return f"{now.year}-{now.year + 1}"
    return f"{now.year - 1}-{now.year}"


def _loading() -> dict:
    return c_card(
        "## 🏆 Trendyol Süper Lig",
        body="`─────────────────` Yükleniyor...",
        color=0xE32429,
    )


class SuperLig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot   = bot
        self._cache: dict[str, tuple[dict, float]] = {}

    # ── API helper ─────────────────────────────────────────────────────────────

    async def _fetch(self, endpoint: str, params: dict | None = None, *, ttl: int = 300) -> dict | None:
        params = params or {}
        cache_key = f"{endpoint}:{sorted(params.items())}"
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if time.time() - ts < ttl:
                return data
        url = f"{API_BASE}{API_KEY}/{endpoint}"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
                async with s.get(url, params=params) as r:
                    text = await r.text()
                    if not text.strip():
                        log.error("TheSportsDB %s → boş yanıt (HTTP %d)", endpoint, r.status)
                        return None
                    try:
                        data = json.loads(text)
                    except Exception:
                        log.error("TheSportsDB %s → JSON parse hatası: %r", endpoint, text[:300])
                        return None
                    if r.status == 200:
                        self._cache[cache_key] = (data, time.time())
                    else:
                        log.warning("TheSportsDB %s → HTTP %d", endpoint, r.status)
                    return data
        except Exception as exc:
            log.error("TheSportsDB hata (%s): %s", endpoint, exc)
        return None

    def _error_card(self, msg: str) -> dict:
        return c_container(
            c_text("## ❌ Hata"),
            c_separator(),
            c_text(msg),
            color=COLORS.DANGER,
        )

    # ── Command group ──────────────────────────────────────────────────────────

    lig = app_commands.Group(name="lig", description="🏆 Trendyol Süper Lig komutları")

    # /lig sıralama ─────────────────────────────────────────────────────────────

    @lig.command(name="sıralama", description="Süper Lig puan tablosunu gösterir.")
    async def siralama(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        season = _current_season()
        data   = await self._fetch("lookuptable.php", {"l": LEAGUE_ID, "s": season})

        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        teams = data.get("table") or []
        if not teams:
            await edit_original(interaction, self._error_card(
                f"Puan tablosu alınamadı.\n-# Sezon: {season} · leagueId: {LEAGUE_ID}"
            ))
            return

        items: list[dict] = [
            c_text(f"## 🏆 Trendyol Süper Lig — Puan Tablosu\n-# {season} Sezonu"),
            c_separator(),
        ]

        for team in teams:
            rank     = int(team.get("intRank") or 0)
            name     = team.get("strTeam", "?")
            pts      = team.get("intPoints", "0")
            oyn      = team.get("intPlayed", "0")
            g        = team.get("intWin", "0")
            b        = team.get("intDraw", "0")
            m        = team.get("intLoss", "0")
            af       = team.get("intGoalsFor", "0")
            ay       = team.get("intGoalsAgainst", "0")
            diff     = _diff_str(team.get("intGoalDifference", 0))
            zone     = _zone(team.get("strDescription") or "")
            badge    = team.get("strTeamBadge") or None
            rank_str = RANK_EMOJI.get(rank, f"`{rank:2d}.`")

            items.append(
                c_section(
                    c_text(f"{rank_str} {zone} **{name}**"),
                    c_text(f"**{pts}P** · O:{oyn} G:{g} B:{b} M:{m} · {af}:{ay} ({diff})"),
                    accessory=c_thumbnail(badge),
                )
            )

        items += [
            c_separator(),
            c_text("-# 🔵 Şampiyonlar Ligi · 🟠 Avrupa Ligi · 🟢 Konferans Ligi · 🔴 Küme Düşme"),
        ]

        await edit_original(interaction, c_container(*items, color=0xE32429))

    # /lig takvim ───────────────────────────────────────────────────────────────

    @lig.command(name="takvim", description="Yaklaşan Süper Lig maçlarını gösterir.")
    async def takvim(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        data = await self._fetch("eventsnextleague.php", {"id": LEAGUE_ID})

        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        events = data.get("events") or []
        if not events:
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
        for ev in events:
            rnd      = str(ev.get("intRound") or "?")
            date_str = ev.get("dateEvent", "")
            time_str = (ev.get("strTime") or "00:00:00")[:5]
            home     = ev.get("strHomeTeam", "?")
            away     = ev.get("strAwayTeam", "?")
            try:
                dt  = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                ts  = int(dt.replace(tzinfo=timezone.utc).timestamp())
                row = f"📅 <t:{ts}:d> <t:{ts}:t> · **{home}** 🆚 **{away}**"
            except (ValueError, TypeError):
                row = f"📅 {date_str} {time_str} · **{home}** 🆚 **{away}**"
            rounds.setdefault(f"Hafta {rnd}", []).append(row)

        sections = [
            f"**📌 {rnd}**\n" + "\n".join(matches)
            for rnd, matches in rounds.items()
        ]

        await edit_original(
            interaction,
            c_container(
                c_text(
                    f"## 📅 Trendyol Süper Lig — Maç Takvimi\n"
                    f"-# Önümüzdeki {len(events)} maç"
                ),
                c_separator(),
                c_text("\n\n".join(sections)),
                c_separator(),
                c_text("-# Saatler UTC · Discord zaman damgaları yerel saatinizi gösterir"),
                color=COLORS.INFO,
            ),
        )

    # /lig sonuçlar ─────────────────────────────────────────────────────────────

    @lig.command(name="sonuçlar", description="Son Süper Lig maç sonuçlarını gösterir.")
    async def sonuclar(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        data = await self._fetch("eventspastleague.php", {"id": LEAGUE_ID})

        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        events = list(reversed(data.get("events") or []))
        if not events:
            await edit_original(
                interaction,
                c_container(
                    c_text("## 📊 Son Sonuçlar"),
                    c_separator(),
                    c_text("Tamamlanmış maç bulunamadı."),
                    color=COLORS.INFO,
                ),
            )
            return

        rounds: dict[str, list[str]] = {}
        for ev in events[:15]:
            rnd    = str(ev.get("intRound") or "?")
            home   = ev.get("strHomeTeam", "?")
            away   = ev.get("strAwayTeam", "?")
            gh_raw = ev.get("intHomeScore")
            ga_raw = ev.get("intAwayScore")
            date_s = ev.get("dateEvent", "")

            try:
                ts       = int(datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
                date_str = f"<t:{ts}:d>"
            except (ValueError, TypeError):
                date_str = date_s

            if gh_raw is not None and ga_raw is not None:
                gh, ga = int(gh_raw), int(ga_raw)
                if gh > ga:
                    row = f"🟩 {date_str} · **{home} {gh}–{ga}** {away}"
                elif ga > gh:
                    row = f"🟩 {date_str} · {home} **{gh}–{ga} {away}**"
                else:
                    row = f"🟨 {date_str} · {home} {gh}–{ga} {away}"
            else:
                row = f"✅ {date_str} · {home} 🆚 {away}"

            rounds.setdefault(f"Hafta {rnd}", []).append(row)

        sections = [
            f"**📌 {rnd}**\n" + "\n".join(matches)
            for rnd, matches in rounds.items()
        ]

        await edit_original(
            interaction,
            c_container(
                c_text("## 📊 Trendyol Süper Lig — Son Sonuçlar"),
                c_separator(),
                c_text("\n\n".join(sections)),
                c_separator(),
                c_text("-# 🟩 Kazanan · 🟨 Beraberlik"),
                color=COLORS.SUCCESS,
            ),
        )

    # /lig canlı ────────────────────────────────────────────────────────────────

    @lig.command(name="canlı", description="Devam eden Süper Lig maçlarının canlı skorlarını gösterir.")
    async def canli(self, interaction: discord.Interaction):
        await respond(interaction, _loading())
        await edit_original(
            interaction,
            c_container(
                c_text("## 🔴 Canlı Maçlar"),
                c_separator(),
                c_text(
                    "Canlı skor özelliği bu API'nin ücretsiz planında mevcut değil.\n"
                    "-# TheSportsDB Patreon aboneliği gerektirir."
                ),
                color=COLORS.NEUTRAL,
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
