import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import random

from ._shared import giphy
from .._v2 import (
    COLORS, c_card, c_text, c_thumbnail, c_section, c_container, c_separator, c_media,
    c_progress, respond, update, channel_send, msg_edit, followup as v2_followup,
)

_EYLEM_EMOJI = {"kılıç": "⚔️", "büyü": "🔮", "kalkan": "🛡️"}
_EYLEM_LABEL = {"kılıç": "Kılıç", "büyü": "Büyü", "kalkan": "Kalkan"}

MAKS_HP  = 150
MAKS_TUR = 20

_ARENA_RED  = 0xB41E1E
_ARENA_GOLD = COLORS.GAME


async def _v2_err(interaction: discord.Interaction, title: str, body: str = "", color: int = COLORS.DANGER):
    thumb = str(interaction.client.user.display_avatar.url)
    if interaction.response.is_done():
        await v2_followup(interaction, c_card(f"## {title}", body=body, thumbnail=thumb, color=color), ephemeral=True)
    else:
        await respond(interaction, c_card(f"## {title}", body=body, thumbnail=thumb, color=color), ephemeral=True)


def _hasar(saldirgan: str, savunmaci: str) -> tuple[int, str]:
    if saldirgan == "kalkan":
        return 0, ""
    if saldirgan == "kılıç":
        if savunmaci == "kalkan":
            return 0, "Kalkan engelledi!"
        dmg = random.randint(20, 35)
        if random.random() < 0.15:
            dmg = int(dmg * 1.6)
            return dmg, f"Kritik Kılıç! {dmg} hasar"
        return dmg, f"Kılıç {dmg} hasar verdi"
    if random.random() > 0.80:
        return 0, "Büyü ıskaladı!"
    dmg = random.randint(30, 45)
    if savunmaci == "kalkan":
        dmg = int(dmg * 0.45)
        return dmg, f"Kalkan büyüyü hafifletti → {dmg} hasar"
    if random.random() < 0.12:
        dmg = int(dmg * 1.6)
        return dmg, f"Kritik Büyü! {dmg} hasar"
    return dmg, f"Büyü {dmg} hasar verdi"


# ── Tekrar Oyna ─────────────────────────────────────────────────────────────────

class ArenaTekrarView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member, son_kart: dict):
        super().__init__(timeout=120)
        self.p1       = p1
        self.p2       = p2
        self.son_kart = son_kart
        self.msg: discord.Message | None = None

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await msg_edit(self.msg, self.son_kart, view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Tekrar Oyna", emoji="🔄", style=discord.ButtonStyle.success)
    async def tekrar(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user.id not in (self.p1.id, self.p2.id):
            return await _v2_err(interaction, "⛔ Erişim", "Bu oyuna dahil değildin.")
        btn.disabled = True
        self.stop()
        await update(interaction, self.son_kart, view=self)
        view = ArenaView(self.p1, self.p2)
        new_msg = await channel_send(interaction.channel, view._card(), view=view)
        view.msg = new_msg


# ── Ana Oyun View ────────────────────────────────────────────────────────────────

class ArenaView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=90)
        self.oyuncular = [p1, p2]
        self.hp        = [MAKS_HP, MAKS_HP]
        self.seçimler: dict[int, str] = {}
        self.tur       = 1
        self.msg: discord.Message | None = None

    def _hp_color(self, hp: int) -> str:
        """HP yüzdesine göre durum emojisi."""
        pct = hp / MAKS_HP
        if pct >= 0.7: return "🟢"
        if pct >= 0.4: return "🟡"
        if pct >= 0.15: return "🟠"
        return "🔴"

    def _player_section(self, member: discord.Member, hp: int, secti: bool, color: int) -> dict:
        bar = c_progress(hp, MAKS_HP, length=15)
        status = "✅ Hazır" if secti else "⏳ Bekleniyor..."
        emoji = self._hp_color(hp)
        text = (
            f"### {emoji} {member.display_name}\n"
            f"`{bar}` `{hp}/{MAKS_HP}` HP\n"
            f"-# {status}"
        )
        return c_section(c_text(text), accessory=c_thumbnail(str(member.display_avatar.url)))

    def _card(self, son_log: str = "") -> dict:
        p1, p2 = self.oyuncular
        items: list[dict] = [
            c_text(f"## ⚔️ Arena Dövüşü\n-# Tur **{self.tur}** / {MAKS_TUR}"),
            c_separator(),
            self._player_section(p1, self.hp[0], p1.id in self.seçimler, _ARENA_RED),
            self._player_section(p2, self.hp[1], p2.id in self.seçimler, _ARENA_RED),
        ]
        if son_log:
            items.append(c_separator())
            items.append(c_text(f"**📜 Son Eylem**\n{son_log}"))
        return c_container(*items, color=_ARENA_RED)

    async def _eylem_seç(self, interaction: discord.Interaction, eylem: str):
        uid = interaction.user.id
        if uid not in (self.oyuncular[0].id, self.oyuncular[1].id):
            return await _v2_err(interaction, "⛔ Erişim", "Bu dövüşe dahil değilsin.")
        if uid in self.seçimler:
            return await _v2_err(interaction, "🔁 Tekrar", "Bu tur için zaten seçim yaptın.", COLORS.WARNING)

        self.seçimler[uid] = eylem
        thumb = str(interaction.client.user.display_avatar.url)
        await respond(interaction,
            c_card(
                f"## {_EYLEM_EMOJI[eylem]} {_EYLEM_LABEL[eylem]} Seçildi",
                body="Rakibin seçimi bekleniyor...",
                thumbnail=thumb,
                color=_ARENA_RED,
            ),
            ephemeral=True,
        )

        assert self.msg
        await msg_edit(self.msg, self._card(), view=self)

        if len(self.seçimler) < 2:
            return

        e1 = self.seçimler[self.oyuncular[0].id]
        e2 = self.seçimler[self.oyuncular[1].id]

        d_on_p2, acik2 = _hasar(e1, e2)
        d_on_p1, acik1 = _hasar(e2, e1)

        self.hp[0] = max(0, self.hp[0] - d_on_p1)
        self.hp[1] = max(0, self.hp[1] - d_on_p2)

        p1n, p2n = self.oyuncular[0].display_name, self.oyuncular[1].display_name
        log_lines = [
            f"{_EYLEM_EMOJI[e1]} **{p1n}** → {_EYLEM_LABEL[e1]}",
            f"{_EYLEM_EMOJI[e2]} **{p2n}** → {_EYLEM_LABEL[e2]}",
        ]
        if acik2:
            log_lines.append(f"┗ **{p1n}:** {acik2}")
        if acik1:
            log_lines.append(f"┗ **{p2n}:** {acik1}")
        son_log = "\n".join(log_lines)

        self.tur += 1
        self.seçimler.clear()

        bitti = self.hp[0] <= 0 or self.hp[1] <= 0 or self.tur > MAKS_TUR
        if bitti:
            self.stop()
            for c in self.children:
                c.disabled = True

            if self.hp[0] <= 0 and self.hp[1] <= 0:
                başlık, renk_int, tag, kazanan_avatar = "🤝 Berabere — İkiniz de yıkıldınız", 0x95A5A6, "tie draw", str(self.oyuncular[0].display_avatar.url)
            elif self.hp[0] <= 0:
                başlık, renk_int, tag, kazanan_avatar = f"🏆 {p2n} Kazandı!", COLORS.SUCCESS, "victory winner", str(self.oyuncular[1].display_avatar.url)
            elif self.hp[1] <= 0:
                başlık, renk_int, tag, kazanan_avatar = f"🏆 {p1n} Kazandı!", COLORS.SUCCESS, "victory winner", str(self.oyuncular[0].display_avatar.url)
            else:
                kazanan = self.oyuncular[0] if self.hp[0] > self.hp[1] else self.oyuncular[1]
                başlık, renk_int, tag, kazanan_avatar = f"⏱️ {kazanan.display_name} Daha Çok Canla Kaldı", _ARENA_GOLD, "victory winner", str(kazanan.display_avatar.url)

            gif = await giphy(tag)

            bar1 = c_progress(self.hp[0], MAKS_HP, length=15)
            bar2 = c_progress(self.hp[1], MAKS_HP, length=15)

            fin_items: list[dict] = [
                c_section(
                    c_text(f"## {başlık}"),
                    accessory=c_thumbnail(kazanan_avatar),
                ),
                c_separator(),
                c_text(
                    f"{self._hp_color(self.hp[0])} **{p1n}**\n"
                    f"`{bar1}` `{self.hp[0]}/{MAKS_HP}`\n\n"
                    f"{self._hp_color(self.hp[1])} **{p2n}**\n"
                    f"`{bar2}` `{self.hp[1]}/{MAKS_HP}`"
                ),
                c_separator(),
                c_text(f"**📜 Son Eylem**\n{son_log}"),
            ]
            if gif:
                fin_items.append(c_separator())
                fin_items.append(c_media(gif))

            son_kart = c_container(*fin_items, color=renk_int)
            tekrar = ArenaTekrarView(self.oyuncular[0], self.oyuncular[1], son_kart)
            await msg_edit(self.msg, son_kart, view=tekrar)
            tekrar.msg = self.msg
            return

        await msg_edit(self.msg, self._card(son_log), view=self)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await msg_edit(self.msg,
                    c_card("## ⏰ Süre Doldu", body="Dövüş süresi içinde tamamlanmadı, oyun iptal edildi.", color=0x95A5A6),
                    view=self,
                )
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Kılıç", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def kılıç_btn(self, i: discord.Interaction, _: discord.ui.Button):
        await self._eylem_seç(i, "kılıç")

    @discord.ui.button(label="Büyü", emoji="🔮", style=discord.ButtonStyle.primary)
    async def büyü_btn(self, i: discord.Interaction, _: discord.ui.Button):
        await self._eylem_seç(i, "büyü")

    @discord.ui.button(label="Kalkan", emoji="🛡️", style=discord.ButtonStyle.secondary)
    async def kalkan_btn(self, i: discord.Interaction, _: discord.ui.Button):
        await self._eylem_seç(i, "kalkan")


# ── Cog ─────────────────────────────────────────────────────────────────────────

class Arena(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="arena", description="Bir oyuncuyla tur bazlı dövüş yap! (Kılıç / Büyü / Kalkan)")
    @app_commands.describe(rakip="Dövüşmek istediğin kişi")
    @app_commands.guild_only()
    async def arena(self, interaction: discord.Interaction, rakip: discord.Member):
        thumb = str(interaction.client.user.display_avatar.url)
        if rakip.id == interaction.user.id:
            return await respond(interaction,
                c_card("## ❌ Hata", body="Kendinle dövüşemezsin!", thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
            )
        if rakip.bot:
            return await respond(interaction,
                c_card("## ❌ Hata", body="Botlarla dövüşemezsin!", thumbnail=thumb, color=COLORS.DANGER),
                ephemeral=True,
            )

        view = ArenaView(interaction.user, rakip)
        view.msg = await respond(interaction, view._card(), view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Arena(bot))
