"""
cogs/sports/superlig.py — Trendyol Süper Lig komutları
- Standings: Wikipedia (full 18-team table)
- Takvim/Sonuçlar: TheSportsDB (free, key 123)
"""
from __future__ import annotations

import json
import logging
import re
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

# ── Wikipedia (standings) ─────────────────────────────────────────────────────
WIKI_BASE   = "https://en.wikipedia.org/wiki/"
WIKI_HEADERS = {"User-Agent": "HorozBot/1.0 (+https://github.com/batuhanbecel/horoz-bot)"}

# ── TheSportsDB (fixtures) ────────────────────────────────────────────────────
TSDB_LEAGUE_ID = 4339
TSDB_BASE      = "https://www.thesportsdb.com/api/v1/json/123/"

RANK_EMOJI = {1: "🥇", 2: "🥈", 3: "🥉"}

ZONE_MAP = {
    "champions": "🔵",
    "europa":    "🟠",
    "conference": "🟢",
    "relegation": "🔴",
}


def _zone(text: str) -> str:
    desc = (text or "").lower()
    for key, emoji in ZONE_MAP.items():
        if key in desc:
            return emoji
    return "⬛"


def _diff_str(val) -> str:
    s = str(val or "0").strip()
    if s.startswith(("+", "-", "−")):
        return s.replace("−", "-")
    try:
        v = int(s)
        return f"+{v}" if v >= 0 else str(v)
    except ValueError:
        return s


def _wiki_season_url() -> str:
    """Mevcut Süper Lig sezonu için Wikipedia URL'si.
    Sezon Ağustos'ta başlar — 2025–26 → '2025%E2%80%9326_Süper_Lig'."""
    now = datetime.now(timezone.utc)
    if now.month >= 7:
        start, end_yy = now.year, (now.year + 1) % 100
    else:
        start, end_yy = now.year - 1, now.year % 100
    season_path = f"{start}%E2%80%93{end_yy:02d}_S%C3%BCper_Lig"
    return WIKI_BASE + season_path


def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = (
        s.replace("&amp;", "&")
         .replace("&lt;", "<")
         .replace("&gt;", ">")
         .replace("&nbsp;", " ")
         .replace("&#160;", " ")
    )
    return re.sub(r"\s+", " ", s).strip()


def _parse_wiki_standings(html: str) -> list[dict]:
    """Wikipedia 'League_table' bölümündeki ilk wikitable'ı parse eder."""
    section = re.search(
        r'id="League_table"[\s\S]+?<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>([\s\S]+?)</table>',
        html,
    )
    if not section:
        log.warning("Wikipedia: League_table bölümü bulunamadı")
        return []

    table_html = section.group(1)
    teams: list[dict] = []

    for row_match in re.finditer(r"<tr[^>]*>([\s\S]+?)</tr>", table_html):
        row_html = row_match.group(1)
        cells_raw = re.findall(r"<t[hd][^>]*>([\s\S]+?)</t[hd]>", row_html)
        if len(cells_raw) < 10:
            continue
        cells = [_strip_html(c) for c in cells_raw]
        try:
            pos = int(cells[0])
        except ValueError:
            continue
        if not (1 <= pos <= 30):
            continue
        team_raw = cells[1]
        team_name = re.sub(r"\s*\([A-Z]\)\s*$", "", team_raw).strip()
        qualification = cells[10] if len(cells) > 10 else ""

        teams.append({
            "position": pos,
            "name": team_name,
            "played": cells[2],
            "wins": cells[3],
            "draws": cells[4],
            "losses": cells[5],
            "gf": cells[6],
            "ga": cells[7],
            "gd": cells[8],
            "points": cells[9],
            "qualification": qualification,
        })

    return teams


def _loading() -> dict:
    return c_card(
        "## 🏆 Trendyol Süper Lig",
        body="`─────────────────` Yükleniyor...",
        color=0xE32429,
    )


class SuperLig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cache: dict[str, tuple[object, float]] = {}

    # ── HTTP ───────────────────────────────────────────────────────────────────

    async def _fetch_text(self, url: str, *, headers: dict | None = None, ttl: int = 300) -> str | None:
        cache_key = f"text:{url}"
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if time.time() - ts < ttl:
                return data  # type: ignore[return-value]
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers=headers or {},
            ) as s:
                async with s.get(url) as r:
                    if r.status != 200:
                        log.warning("HTTP %d → %s", r.status, url)
                        return None
                    text = await r.text()
                    self._cache[cache_key] = (text, time.time())
                    return text
        except Exception as exc:
            log.error("HTTP hatası %s: %s", url, exc)
        return None

    async def _fetch_json(self, url: str, *, ttl: int = 300) -> dict | None:
        cache_key = f"json:{url}"
        if cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if time.time() - ts < ttl:
                return data  # type: ignore[return-value]
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
                async with s.get(url) as r:
                    text = await r.text()
                    if not text.strip():
                        return None
                    try:
                        data = json.loads(text)
                    except Exception:
                        log.error("JSON parse hatası: %r", text[:200])
                        return None
                    if r.status == 200:
                        self._cache[cache_key] = (data, time.time())
                    return data
        except Exception as exc:
            log.error("API hatası %s: %s", url, exc)
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

        url = _wiki_season_url()
        html = await self._fetch_text(url, headers=WIKI_HEADERS)
        if not html:
            await edit_original(interaction, self._error_card("Wikipedia'ya ulaşılamadı."))
            return

        teams = _parse_wiki_standings(html)
        log.info("Wikipedia standings: %d teams", len(teams))
        if not teams:
            await edit_original(
                interaction,
                self._error_card("Puan tablosu çıkarılamadı. Sezon sayfası henüz yayında olmayabilir."),
            )
            return

        season_label = url.rsplit("/", 1)[-1].replace("%E2%80%93", "–").replace("S%C3%BCper", "Süper").replace("_", " ")

        rows: list[str] = []
        for t in teams:
            rank = t["position"]
            name = t["name"]
            zone = _zone(t["qualification"])
            diff = _diff_str(t["gd"])
            rank_str = RANK_EMOJI.get(rank, f"`{rank:2d}.`")
            rows.append(
                f"{rank_str} {zone} **{name}** — **{t['points']}P**"
                f" · O:{t['played']} G:{t['wins']} B:{t['draws']} M:{t['losses']}"
                f" · {t['gf']}:{t['ga']} ({diff})"
            )

        top, bot = rows[:10], rows[10:]
        body_items: list[dict] = [c_text("\n".join(top))]
        if bot:
            body_items += [c_separator(spacing=1), c_text("\n".join(bot))]

        await edit_original(
            interaction,
            c_container(
                c_text(f"## 🏆 Trendyol Süper Lig — Puan Tablosu\n-# {season_label}"),
                c_separator(),
                *body_items,
                c_separator(),
                c_text("-# 🔵 Şampiyonlar Ligi · 🟠 Avrupa Ligi · 🟢 Konferans Ligi · 🔴 Küme Düşme · Kaynak: Wikipedia"),
                color=0xE32429,
            ),
        )

    # /lig takvim ───────────────────────────────────────────────────────────────

    @lig.command(name="takvim", description="Yaklaşan Süper Lig maçlarını gösterir.")
    async def takvim(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        data = await self._fetch_json(f"{TSDB_BASE}eventsnextleague.php?id={TSDB_LEAGUE_ID}")
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
                c_text("-# Saatler yerel saatinizde gösterilir · Kaynak: TheSportsDB"),
                color=COLORS.INFO,
            ),
        )

    # /lig sonuçlar ─────────────────────────────────────────────────────────────

    @lig.command(name="sonuçlar", description="Son Süper Lig maç sonuçlarını gösterir.")
    async def sonuclar(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        data = await self._fetch_json(f"{TSDB_BASE}eventspastleague.php?id={TSDB_LEAGUE_ID}")
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
                c_text("-# 🟩 Kazanan kalın · 🟨 Beraberlik · Kaynak: TheSportsDB"),
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
                    "Canlı skor özelliği şu an aktif değil.\n"
                    "-# Ücretsiz veri kaynaklarımızda canlı skor mevcut değil."
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
