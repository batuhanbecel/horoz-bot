"""
cogs/sports/superlig.py — Trendyol Süper Lig komutları
API: Sofascore (api.sofascore.com) — anahtar gerektirmez
"""
from __future__ import annotations

import json
import logging
import time

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

TOURNAMENT_ID = 52  # Turkish Super Lig — Sofascore unique-tournament
API_BASE      = "https://api.sofascore.com/api/v1"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

RANK_EMOJI = {1: "🥇", 2: "🥈", 3: "🥉"}

ZONE_MAP = {
    "champions league":  "🔵",
    "europa league":     "🟠",
    "conference league": "🟢",
    "relegation":        "🔴",
}


def _zone(text: str) -> str:
    desc = (text or "").lower()
    for key, emoji in ZONE_MAP.items():
        if key in desc:
            return emoji
    return "⬛"


def _diff_str(g_for: int, g_against: int) -> str:
    diff = int(g_for or 0) - int(g_against or 0)
    return f"+{diff}" if diff >= 0 else str(diff)


def _loading() -> dict:
    return c_card(
        "## 🏆 Trendyol Süper Lig",
        body="`─────────────────` Yükleniyor...",
        color=0xE32429,
    )


class SuperLig(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cache: dict[str, tuple[dict, float]] = {}
        self._season: tuple[int, str, float] | None = None  # (id, name, ts)

    # ── API helpers ────────────────────────────────────────────────────────────

    async def _fetch(self, path: str, *, ttl: int = 300) -> dict | None:
        if path in self._cache:
            data, ts = self._cache[path]
            if time.time() - ts < ttl:
                return data
        url = f"{API_BASE}{path}"
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers=HEADERS,
            ) as s:
                async with s.get(url) as r:
                    text = await r.text()
                    if not text.strip():
                        log.error("Sofascore %s → boş yanıt (HTTP %d)", path, r.status)
                        return None
                    try:
                        data = json.loads(text)
                    except Exception:
                        log.error("Sofascore %s → JSON parse hatası: %r", path, text[:300])
                        return None
                    if r.status == 200:
                        self._cache[path] = (data, time.time())
                    else:
                        log.warning("Sofascore %s → HTTP %d", path, r.status)
                    return data
        except Exception as exc:
            log.error("Sofascore hata (%s): %s", path, exc)
        return None

    async def _current_season(self) -> tuple[int, str] | None:
        """En güncel sezon ID + adı. 1 saat cache."""
        if self._season and time.time() - self._season[2] < 3600:
            return self._season[0], self._season[1]
        data = await self._fetch(f"/unique-tournament/{TOURNAMENT_ID}/seasons", ttl=3600)
        if not data:
            return None
        seasons = data.get("seasons") or []
        if not seasons:
            return None
        first = seasons[0]
        sid, name = int(first["id"]), str(first.get("name") or "")
        self._season = (sid, name, time.time())
        return sid, name

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

        season = await self._current_season()
        if not season:
            await edit_original(interaction, self._error_card("Sezon bilgisi alınamadı."))
            return
        sid, sname = season

        data = await self._fetch(
            f"/unique-tournament/{TOURNAMENT_ID}/season/{sid}/standings/total"
        )
        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        standings = data.get("standings") or []
        rows_data = (standings[0].get("rows") if standings else []) or []
        log.info("Sofascore standings: %d teams", len(rows_data))
        if not rows_data:
            await edit_original(interaction, self._error_card(f"Puan tablosu boş.\n-# Sezon: {sname}"))
            return

        rows: list[str] = []
        for entry in rows_data:
            rank = int(entry.get("position") or 0)
            team = entry.get("team") or {}
            name = team.get("name", "?")
            pts  = entry.get("points", 0)
            oyn  = entry.get("matches", 0)
            g    = entry.get("wins", 0)
            b    = entry.get("draws", 0)
            m    = entry.get("losses", 0)
            af   = entry.get("scoresFor", 0)
            ay   = entry.get("scoresAgainst", 0)
            diff = _diff_str(af, ay)
            promo_text = ((entry.get("promotion") or {}).get("text")) or ""
            zone = _zone(promo_text)
            rank_str = RANK_EMOJI.get(rank, f"`{rank:2d}.`")
            rows.append(
                f"{rank_str} {zone} **{name}** — **{pts}P**"
                f" · O:{oyn} G:{g} B:{b} M:{m} · {af}:{ay} ({diff})"
            )

        top, bot = rows[:10], rows[10:]
        body_items: list[dict] = [c_text("\n".join(top))]
        if bot:
            body_items += [c_separator(spacing=1), c_text("\n".join(bot))]

        await edit_original(
            interaction,
            c_container(
                c_text(f"## 🏆 Trendyol Süper Lig — Puan Tablosu\n-# {sname}"),
                c_separator(),
                *body_items,
                c_separator(),
                c_text("-# 🔵 Şampiyonlar Ligi · 🟠 Avrupa Ligi · 🟢 Konferans Ligi · 🔴 Küme Düşme"),
                color=0xE32429,
            ),
        )

    # /lig takvim ───────────────────────────────────────────────────────────────

    @lig.command(name="takvim", description="Yaklaşan Süper Lig maçlarını gösterir.")
    async def takvim(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        season = await self._current_season()
        if not season:
            await edit_original(interaction, self._error_card("Sezon bilgisi alınamadı."))
            return
        sid, _ = season

        data = await self._fetch(
            f"/unique-tournament/{TOURNAMENT_ID}/season/{sid}/events/next/0"
        )
        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        events = data.get("events") or []
        upcoming = [
            e for e in events
            if (e.get("status") or {}).get("type") in ("notstarted", "delayed")
        ]
        if not upcoming:
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
        for ev in upcoming[:20]:
            rnd  = (ev.get("roundInfo") or {}).get("round") or "?"
            home = (ev.get("homeTeam") or {}).get("name", "?")
            away = (ev.get("awayTeam") or {}).get("name", "?")
            ts   = int(ev.get("startTimestamp") or 0)
            row  = (
                f"📅 <t:{ts}:d> <t:{ts}:t> · **{home}** 🆚 **{away}**"
                if ts else f"📅 **{home}** 🆚 **{away}**"
            )
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
                    f"-# Önümüzdeki {min(len(upcoming), 20)} maç"
                ),
                c_separator(),
                c_text("\n\n".join(sections)),
                c_separator(),
                c_text("-# Saatler yerel saatinizde gösterilir"),
                color=COLORS.INFO,
            ),
        )

    # /lig sonuçlar ─────────────────────────────────────────────────────────────

    @lig.command(name="sonuçlar", description="Son Süper Lig maç sonuçlarını gösterir.")
    async def sonuclar(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        season = await self._current_season()
        if not season:
            await edit_original(interaction, self._error_card("Sezon bilgisi alınamadı."))
            return
        sid, _ = season

        data = await self._fetch(
            f"/unique-tournament/{TOURNAMENT_ID}/season/{sid}/events/last/0"
        )
        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        events = data.get("events") or []
        finished = [
            e for e in events
            if (e.get("status") or {}).get("type") == "finished"
        ]
        # Sofascore last/0 chronological asc; reverse to get most recent first
        finished.reverse()
        if not finished:
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
        for ev in finished[:15]:
            rnd  = (ev.get("roundInfo") or {}).get("round") or "?"
            home = (ev.get("homeTeam") or {}).get("name", "?")
            away = (ev.get("awayTeam") or {}).get("name", "?")
            gh   = (ev.get("homeScore") or {}).get("current")
            ga   = (ev.get("awayScore") or {}).get("current")
            ts   = int(ev.get("startTimestamp") or 0)
            date_str = f"<t:{ts}:d>" if ts else ""

            if gh is not None and ga is not None:
                gh, ga = int(gh), int(ga)
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
                c_text("-# 🟩 Kazanan kalın · 🟨 Beraberlik"),
                color=COLORS.SUCCESS,
            ),
        )

    # /lig canlı ────────────────────────────────────────────────────────────────

    @lig.command(name="canlı", description="Devam eden Süper Lig maçlarının canlı skorlarını gösterir.")
    async def canli(self, interaction: discord.Interaction):
        await respond(interaction, _loading())

        data = await self._fetch("/sport/football/events/live", ttl=60)
        if not data:
            await edit_original(interaction, self._error_card("API'ye ulaşılamadı."))
            return

        events = data.get("events") or []
        live = [
            e for e in events
            if ((e.get("tournament") or {}).get("uniqueTournament") or {}).get("id") == TOURNAMENT_ID
            and (e.get("status") or {}).get("type") == "inprogress"
        ]

        if not live:
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
        for ev in live:
            home   = (ev.get("homeTeam") or {}).get("name", "?")
            away   = (ev.get("awayTeam") or {}).get("name", "?")
            gh     = (ev.get("homeScore") or {}).get("current") or 0
            ga     = (ev.get("awayScore") or {}).get("current") or 0
            status = (ev.get("status") or {}).get("description", "")
            rows.append(f"🔴 **{status}** · **{home} {gh}–{ga} {away}**")

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
