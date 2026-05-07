"""
cogs/sports/superlig.py — Trendyol Süper Lig komutları
API: allsportsapi.com v3 (ücretsiz, 200 istek/ay)
Env: ALLSPORTS_API_KEY
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

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

LEAGUE_ID = 322               # Trendyol Süper Lig — allsportsapi.com
API_BASE  = "https://apiv2.allsportsapi.com/football/"

RANK_EMOJI = {1: "🥇", 2: "🥈", 3: "🥉"}

ZONE_MAP = {
    "champions league":  "🔵",
    "europa league":     "🟠",
    "conference league": "🟢",
    "relegation":        "🔴",
    "playoff":           "🔴",
}


def _zone(place_type: str) -> str:
    pt = (place_type or "").lower()
    for key, emoji in ZONE_MAP.items():
        if key in pt:
            return emoji
    return "⬛"


def _diff_str(raw: str | int) -> str:
    """'+35', '-10' veya raw int'i düzgün formatlar."""
    try:
        v = int(str(raw).replace("+", ""))
        return f"+{v}" if v >= 0 else str(v)
    except (ValueError, TypeError):
        return str(raw)


def _parse_score(result: str) -> tuple[int, int] | None:
    """'2 - 1' → (2, 1). Ayrıştırılamazsa None."""
    parts = [p.strip() for p in result.split("-")]
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return int(parts[0]), int(parts[1])
    return None


def _round_label(rnd: str) -> str:
    return (
        (rnd or "")
        .replace("Week ", "Hafta ")
        .replace("Regular Season - ", "Hafta ")
        .replace("Round ", "Hafta ")
    )


def _extract_standings(result) -> tuple[list[dict], str]:
    """AllSportsAPI v2 standings result → (takım listesi, sezon).

    API formatı (v2 docs p.15):
      result = {"total": [team, ...], "home": [...], "away": [...]}
    Fallback olarak list[dict] ve düz dict de desteklenir.
    """
    teams: list[dict] = []
    season = ""

    if isinstance(result, dict):
        # Normal format: {"total": [...], "home": [...], "away": [...]}
        total = result.get("total") or []
        if isinstance(total, list) and total:
            teams = [t for t in total if isinstance(t, dict)]
            season = (teams[0].get("league_season") or "") if teams else ""
            return teams, season
        # Fallback: herhangi bir list değeri
        for val in result.values():
            if isinstance(val, list) and val:
                teams = [t for t in val if isinstance(t, dict)]
                if teams:
                    season = (teams[0].get("league_season") or "")
                    return teams, season

    elif isinstance(result, list):
        for item in result:
            if not isinstance(item, dict):
                continue
            if "standing_place" in item:
                teams.append(item)
            else:
                nested = item.get("league_standings") or item.get("standings")
                if isinstance(nested, dict):
                    for group in nested.values():
                        if isinstance(group, list):
                            teams.extend(t for t in group if isinstance(t, dict))
                elif isinstance(nested, list):
                    teams.extend(t for t in nested if isinstance(t, dict))
        if teams:
            season = (teams[0].get("league_season") or "")

    return teams, season


def _loading() -> dict:
    return c_card(
        "## 🏆 Trendyol Süper Lig",
        body="`─────────────────` Yükleniyor...",
        color=0xE32429,
    )


class SuperLig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._key  = os.getenv("ALLSPORTS_API_KEY", "")
        self._cache: dict[str, tuple[dict, float]] = {}

    # ── API helpers ────────────────────────────────────────────────────────────

    async def _fetch(self, met: str, params: dict, *, ttl: int = 300) -> dict | None:
        """apiv3.allsportsapi.com/football/ — met= parametresiyle istek atar."""
        if not self._key:
            return None
        cache_key = f"{met}:{sorted(params.items())}"
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if time.time() - ts < ttl:
                return data
        query = {"met": met, "APIkey": self._key, **params}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
                async with s.get(API_BASE, params=query) as r:
                    text = await r.text()
                    if not text.strip():
                        log.error("AllSportsAPI %s → boş yanıt (HTTP %d). URL: %s", met, r.status, r.url)
                        return None
                    try:
                        data = json.loads(text)
                    except Exception:
                        log.error("AllSportsAPI %s → JSON parse hatası. İlk 300 karakter: %r", met, text[:300])
                        return None
                    if r.status == 200:
                        self._cache[cache_key] = (data, time.time())
                    else:
                        log.warning("AllSportsAPI %s %s → HTTP %d", met, params, r.status)
                    return data
        except Exception as exc:
            log.error("AllSportsAPI hata (%s): %s", met, exc)
        return None

    async def _get_season_id(self) -> str | None:
        """League 322 için mevcut sezon ID'sini döndürür."""
        data = await self._fetch("Leagues", {"leagueId": LEAGUE_ID}, ttl=3600)
        if not data:
            return None
        result = data.get("result") or []
        log.warning("Leagues result: %r", str(result)[:600])
        if isinstance(result, list) and result:
            league = result[0]
            seasons = league.get("league_seasons") or []
            if seasons:
                latest = max(seasons, key=lambda s: s.get("season_id", 0))
                log.warning("Using season_id=%s", latest.get("season_id"))
                return str(latest.get("season_id", ""))
        return None

    def _no_key_card(self) -> dict:
        return c_container(
            c_text("## ❌ API Anahtarı Eksik"),
            c_separator(),
            c_text(
                "`.env` dosyasına `ALLSPORTS_API_KEY` eklemen gerekiyor.\n"
                "Ücretsiz (200 istek/ay): **allsportsapi.com**"
            ),
            color=COLORS.DANGER,
        )

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

        if not self._key:
            await edit_original(interaction, self._no_key_card())
            return

        data = await self._fetch("Standings", {"leagueId": LEAGUE_ID})

        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        # Debug: fixtures kontrolü — leagueId=322 gerçekten veri döndürüyor mu?
        today = datetime.now(timezone.utc)
        fix_data = await self._fetch(
            "Fixtures",
            {"leagueId": LEAGUE_ID,
             "from": (today - timedelta(days=14)).strftime("%Y-%m-%d"),
             "to": today.strftime("%Y-%m-%d")},
            ttl=60,
        )
        fix_count = len((fix_data or {}).get("result") or []) if fix_data else 0
        log.warning("Fixtures test leagueId=%d last14days count=%d", LEAGUE_ID, fix_count)
        if fix_data and fix_count:
            sample = (fix_data.get("result") or [])[0]
            log.warning("Fixtures sample: %r", str(sample)[:400])

        raw = data.get("result")
        teams, season = _extract_standings(raw)
        if not data.get("success") or not teams:
            await edit_original(interaction, self._error_card(
                f"Puan tablosu alınamadı.\n"
                f"-# success={data.get('success')} · result type={type(raw).__name__} · leagueId={LEAGUE_ID}"
            ))
            return

        rows: list[str] = []
        for team in teams:
            rank = int(team.get("standing_place") or 0)
            name = team.get("standing_team", "?")
            pts  = team.get("standing_PTS", "0")
            oyn  = team.get("standing_P", "0")
            g    = team.get("standing_W", "0")
            b    = team.get("standing_D", "0")
            m    = team.get("standing_L", "0")
            af   = team.get("standing_F", "0")
            ay   = team.get("standing_A", "0")
            diff = _diff_str(team.get("standing_GD", "0"))
            zone = _zone(team.get("standing_place_type", ""))
            rank_str = RANK_EMOJI.get(rank, f"`{rank:2d}.`")

            rows.append(
                f"{rank_str} {zone} **{name}** — **{pts}P**"
                f" · O:{oyn} G:{g} B:{b} M:{m} · {af}:{ay} ({diff})"
            )

        mid = (len(rows) + 1) // 2

        await edit_original(
            interaction,
            c_container(
                c_text(
                    f"## 🏆 Trendyol Süper Lig — Puan Tablosu\n"
                    f"-# {season} Sezonu"
                ),
                c_separator(),
                c_text("\n\n".join(rows[:mid])),
                c_separator(),
                c_text("\n\n".join(rows[mid:])),
                c_separator(),
                c_text("-# 🔵 Şampiyonlar Ligi · 🟠 Avrupa Ligi · 🟢 Konferans Ligi · 🔴 Küme Düşme"),
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

        today  = datetime.now(timezone.utc)
        from_s = today.strftime("%Y-%m-%d")
        to_s   = (today + timedelta(days=21)).strftime("%Y-%m-%d")

        data = await self._fetch("Fixtures", {"leagueId": LEAGUE_ID, "from": from_s, "to": to_s})

        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        events = data.get("result") or []
        # Oynanmamış maçlar: result "-" ve status boş
        fixtures = [
            e for e in events
            if (e.get("event_final_result") or "-").strip() == "-"
            and not (e.get("event_status") or "").strip()
        ]

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
            rnd      = fix.get("league_round", "")
            date_str = fix.get("event_date", "")
            time_str = (fix.get("event_time") or "00:00").strip()
            home     = fix.get("event_home_team", "?")
            away     = fix.get("event_away_team", "?")
            try:
                dt  = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                ts  = int(dt.replace(tzinfo=timezone.utc).timestamp())
                row = f"📅 <t:{ts}:d> <t:{ts}:t> · **{home}** 🆚 **{away}**"
            except (ValueError, TypeError):
                row = f"📅 {date_str} {time_str} · **{home}** 🆚 **{away}**"
            rounds.setdefault(rnd, []).append(row)

        sections = [
            f"**📌 {_round_label(r)}**\n" + "\n".join(m)
            for r, m in rounds.items()
        ]

        await edit_original(
            interaction,
            c_container(
                c_text(
                    f"## 📅 Trendyol Süper Lig — Maç Takvimi\n"
                    f"-# Önümüzdeki {len(fixtures)} maç"
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

        if not self._key:
            await edit_original(interaction, self._no_key_card())
            return

        today  = datetime.now(timezone.utc)
        from_s = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        to_s   = today.strftime("%Y-%m-%d")

        data = await self._fetch("Fixtures", {"leagueId": LEAGUE_ID, "from": from_s, "to": to_s})

        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        events = data.get("result") or []
        # Tamamlanmış maçlar: status "Finished" veya result hane içeriyor
        finished = [
            e for e in reversed(events)
            if (e.get("event_status") or "").strip().lower() == "finished"
            or _parse_score(e.get("event_final_result") or "-") is not None
        ]

        if not finished:
            await edit_original(
                interaction,
                c_container(
                    c_text("## 📊 Son Sonuçlar"),
                    c_separator(),
                    c_text("Son 30 günde tamamlanmış maç bulunamadı."),
                    color=COLORS.INFO,
                ),
            )
            return

        rounds: dict[str, list[str]] = {}
        for fix in finished[:15]:
            rnd    = fix.get("league_round", "")
            date_s = fix.get("event_date", "")
            home   = fix.get("event_home_team", "?")
            away   = fix.get("event_away_team", "?")
            result = (fix.get("event_final_result") or "?").strip()

            try:
                ts       = int(datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
                date_str = f"<t:{ts}:d>"
            except (ValueError, TypeError):
                date_str = date_s

            score = _parse_score(result)
            if score:
                gh, ga = score
                if gh > ga:
                    row = f"🟩 {date_str} · **{home} {gh}–{ga}** {away}"
                elif ga > gh:
                    row = f"🟩 {date_str} · {home} **{gh}–{ga} {away}**"
                else:
                    row = f"🟨 {date_str} · {home} {gh}–{ga} {away}"
            else:
                row = f"✅ {date_str} · {home} **{result}** {away}"

            rounds.setdefault(rnd, []).append(row)

        sections = [
            f"**📌 {_round_label(r)}**\n" + "\n".join(m)
            for r, m in rounds.items()
        ]

        await edit_original(
            interaction,
            c_container(
                c_text("## 📊 Trendyol Süper Lig — Son Sonuçlar"),
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

        data = await self._fetch("Livescore", {"leagueId": LEAGUE_ID}, ttl=60)

        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        all_live = data.get("result") or []
        fixtures = [e for e in all_live if e.get("event_live") == "1"]

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
            home   = fix.get("event_home_team", "?")
            away   = fix.get("event_away_team", "?")
            result = (fix.get("event_final_result") or "? - ?").strip()
            status = (fix.get("event_status") or "?").strip()
            score  = _parse_score(result)
            score_str = f"{score[0]}–{score[1]}" if score else result
            rows.append(f"🔴 **{status}'** · **{home} {score_str} {away}**")

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
