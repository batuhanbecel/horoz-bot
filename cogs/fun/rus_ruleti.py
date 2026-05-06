import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from ._shared import giphy
from .._v2 import (
    COLORS, c_text, c_thumbnail, c_section, c_container, c_separator, c_media,
    c_card, c_progress, respond, update, channel_send, msg_edit, error_response, followup as v2_followup,
)

MAX_OYUNCU = 6
LOBI_SURE  = 60
TETIK_SURE = 45


def _ihtimal_bar(kalan_oda: int) -> str:
    """6 odadan kaçının dolu/boş olduğunu görsel olarak gösterir."""
    toplam = 6
    ateşlendi = toplam - kalan_oda
    return "🔴" * kalan_oda + "⚫" * ateşlendi


async def _ephemeral_err(interaction: discord.Interaction, title: str, body: str = "", color: int = COLORS.DANGER):
    thumb = str(interaction.client.user.display_avatar.url)
    if interaction.response.is_done():
        await v2_followup(interaction, c_card(f"## {title}", body=body, thumbnail=thumb, color=color), ephemeral=True)
    else:
        await respond(interaction, c_card(f"## {title}", body=body, thumbnail=thumb, color=color), ephemeral=True)


class RusRuletiOyun:
    def __init__(self, oyuncular: list[discord.Member]):
        self.oyuncular  = list(oyuncular)
        self.kalan_oda  = 6
        self.mevcut_idx = 0

    @property
    def mevcut_oyuncu(self) -> discord.Member:
        return self.oyuncular[self.mevcut_idx % len(self.oyuncular)]

    def tetik_cek(self) -> tuple[bool, float]:
        ihtimal = 1 / self.kalan_oda
        öldü    = random.random() < ihtimal
        self.kalan_oda -= 1
        if not öldü:
            self.mevcut_idx = (self.mevcut_idx + 1) % len(self.oyuncular)
        return öldü, ihtimal


# ── Lobi ──────────────────────────────────────────────────────────────────────

class LobiView(discord.ui.View):
    def __init__(self, başlatan: discord.Member):
        super().__init__(timeout=LOBI_SURE)
        self.başlatan  = başlatan
        self.oyuncular = [başlatan]
        self.msg: discord.Message | None = None
        self.started   = False

    def _card(self) -> tuple[dict, ...]:
        bar = c_progress(len(self.oyuncular), MAX_OYUNCU, length=12)
        oyuncu_listesi = "\n".join(f"🪑 {o.mention}" for o in self.oyuncular)
        return (c_container(
            c_section(
                c_text(f"## 🔫 Rus Ruleti — Lobi"),
                accessory=c_thumbnail(str(self.başlatan.display_avatar.url)),
            ),
            c_separator(),
            c_text(
                f"`{bar}` `{len(self.oyuncular)}/{MAX_OYUNCU}` oyuncu\n\n"
                f"{oyuncu_listesi}"
            ),
            c_separator(),
            c_text(f"-# 👑 Kurucu: {self.başlatan.mention} · ⏱️ Lobi süresi: {LOBI_SURE}sn"),
            color=COLORS.DANGER,
        ),)

    @discord.ui.button(label="Katıl", emoji="✋", style=discord.ButtonStyle.success)
    async def katıl(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user in self.oyuncular:
            return await _ephemeral_err(interaction, "⚠️ Zaten Lobide", "Lobiye zaten katıldın.", COLORS.WARNING)
        if len(self.oyuncular) >= MAX_OYUNCU:
            return await _ephemeral_err(interaction, "🚫 Lobi Dolu", f"Lobi `{MAX_OYUNCU}/{MAX_OYUNCU}` dolu.")
        self.oyuncular.append(interaction.user)
        if len(self.oyuncular) >= MAX_OYUNCU:
            btn.disabled = True
        await update(interaction, *self._card(), view=self)

    @discord.ui.button(label="Ayrıl", emoji="🚪", style=discord.ButtonStyle.secondary)
    async def ayrıl(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyuncular:
            return await _ephemeral_err(interaction, "❌ Lobide Değilsin", "Lobiye dahil değilsin.")
        if interaction.user == self.başlatan:
            return await _ephemeral_err(interaction, "👑 Kurucu Ayrılamaz", "Lobi kapatmak için **İptal** butonunu kullan.", COLORS.WARNING)
        self.oyuncular.remove(interaction.user)
        for c in self.children:
            if hasattr(c, "label") and c.label == "Katıl":
                c.disabled = False
        await update(interaction, *self._card(), view=self)

    @discord.ui.button(label="Başlat", emoji="▶️", style=discord.ButtonStyle.primary)
    async def başlat(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user.id != self.başlatan.id:
            return await _ephemeral_err(interaction, "🚫 Yetki Yok", "Sadece **kurucu** oyunu başlatabilir.")
        if len(self.oyuncular) < 2:
            return await _ephemeral_err(interaction, "⚠️ Yetersiz Oyuncu", "En az **2 oyuncu** gerekli.", COLORS.WARNING)
        self.started = True
        for c in self.children:
            c.disabled = True
        await update(interaction,
            c_card("## 🔫 Rus Ruleti", body="Oyun başlıyor... silah dolduruluyor 🎯", color=COLORS.DANGER),
            view=self,
        )
        self.stop()
        await _oyunu_başlat(interaction, self.oyuncular)

    @discord.ui.button(label="İptal", emoji="✖️", style=discord.ButtonStyle.danger)
    async def iptal(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user.id != self.başlatan.id:
            return await _ephemeral_err(interaction, "🚫 Yetki Yok", "Sadece **kurucu** iptal edebilir.")
        self.started = True
        self.stop()
        for c in self.children:
            c.disabled = True
        await update(interaction,
            c_card("## 🚫 Lobi İptal Edildi", body=f"{interaction.user.mention} lobi iptal etti.", color=0x95A5A6),
            view=self,
        )

    async def on_timeout(self):
        if self.started:
            return
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await msg_edit(self.msg,
                    c_card("## ⏰ Lobi Süresi Doldu", body="Yeterli sayıda oyuncu toplanmadı.", color=0x95A5A6),
                    view=self,
                )
            except discord.HTTPException:
                pass


# ── Oyun Görünümü ─────────────────────────────────────────────────────────────

def _tetik_card(oyun: RusRuletiOyun, *, sonuç_metni: str = "", color: int = COLORS.DANGER) -> dict:
    """Tetiği çekme kartı: oyuncu avatarı + ihtimal görseli + sıra."""
    oyuncu  = oyun.mevcut_oyuncu
    ihtimal = round(100 / oyun.kalan_oda) if oyun.kalan_oda > 0 else 100
    bar = c_progress(ihtimal, 100, length=14)

    items: list[dict] = [
        c_section(
            c_text(f"## 🔫 Rus Ruleti\n### 🎯 Sıra: {oyuncu.mention}"),
            accessory=c_thumbnail(str(oyuncu.display_avatar.url)),
        ),
        c_separator(),
        c_text(
            f"**🎲 Tehlike**\n"
            f"`{bar}` `%{ihtimal}` ölüm ihtimali\n\n"
            f"**🔫 Silah**\n"
            f"{_ihtimal_bar(oyun.kalan_oda)}\n"
            f"`{oyun.kalan_oda}/6` oda dolu"
        ),
        c_separator(),
        c_text("**🪑 Oyuncular:** " + " · ".join(o.mention for o in oyun.oyuncular)),
    ]
    if sonuç_metni:
        items.append(c_separator())
        items.append(c_text(sonuç_metni))
    return c_container(*items, color=color)


class TetikView(discord.ui.View):
    def __init__(self, oyun: RusRuletiOyun, kanal: discord.abc.Messageable):
        super().__init__(timeout=TETIK_SURE)
        self.oyun        = oyun
        self.kanal       = kanal
        self.msg: discord.Message | None = None
        self._tamamlandı = False

    @discord.ui.button(label="Tetiği Çek", emoji="🔫", style=discord.ButtonStyle.danger)
    async def tetik(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user.id != self.oyun.mevcut_oyuncu.id:
            return await _ephemeral_err(
                interaction, "⛔ Sıra Sende Değil",
                f"Sıra: {self.oyun.mevcut_oyuncu.mention}",
                COLORS.WARNING,
            )
        self._tamamlandı = True
        self.stop()

        öldü, ihtimal = self.oyun.tetik_cek()

        if öldü:
            kurban = interaction.user
            for c in self.children:
                c.disabled = True
            gif = await giphy("bang gunshot")
            items: list[dict] = [
                c_section(
                    c_text(f"## 💀 BANG!\n### {kurban.mention} öldü."),
                    accessory=c_thumbnail(str(kurban.display_avatar.url)),
                ),
                c_separator(),
                c_text(
                    f"🎯 `%{round(ihtimal * 100)}` ihtimale rağmen kurşun {kurban.display_name}'in payına düştü."
                ),
            ]
            if gif:
                items.append(c_separator())
                items.append(c_media(gif))
            await update(interaction, c_container(*items, color=COLORS.DANGER), view=self)
            await asyncio.sleep(2)
            await _oyun_bitti(interaction, self.oyun, kurban)
        else:
            for c in self.children:
                c.disabled = True
            await update(interaction, c_container(
                c_section(
                    c_text(f"## 😮‍💨 Click...\n### {interaction.user.mention} hayatta!"),
                    accessory=c_thumbnail(str(interaction.user.display_avatar.url)),
                ),
                c_separator(),
                c_text(
                    f"Tetik çekildi — **boş**.\n\n"
                    f"**🔫 Silah:** {_ihtimal_bar(self.oyun.kalan_oda)}  `{self.oyun.kalan_oda}/6`"
                ),
                color=COLORS.WARNING,
            ), view=self)
            await asyncio.sleep(1.5)
            await _sonraki_tur(interaction, self.oyun)

    async def on_timeout(self):
        if self._tamamlandı:
            return
        oyuncu = self.oyun.mevcut_oyuncu
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await msg_edit(self.msg, c_container(
                    c_section(
                        c_text(f"## ⏰ Süre Doldu\n### {oyuncu.mention} korktu! 🐔"),
                        accessory=c_thumbnail(str(oyuncu.display_avatar.url)),
                    ),
                    c_separator(),
                    c_text(f"**Süre içinde tetik çekilmedi — oyun sona erdi.**"),
                    color=0x95A5A6,
                ), view=self)
            except discord.HTTPException:
                pass


class TekrarOynaView(discord.ui.View):
    def __init__(self, oyuncular: list[discord.Member], başlatan: discord.Member, son_kart: tuple[dict, ...]):
        super().__init__(timeout=60)
        self.oyuncular = oyuncular
        self.başlatan  = başlatan
        self.son_kart  = son_kart
        self.msg: discord.Message | None = None

    @discord.ui.button(label="Tekrar Oyna", emoji="🔄", style=discord.ButtonStyle.success)
    async def tekrar(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyuncular:
            return await _ephemeral_err(interaction, "🚫 Erişim", "Bu oyuna dahil değildin.")
        btn.disabled = True
        self.stop()
        await update(interaction, *self.son_kart, view=self)
        lobi = LobiView(interaction.user)
        new_msg = await channel_send(interaction.channel, *lobi._card(), view=lobi)
        lobi.msg = new_msg

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await msg_edit(self.msg, *self.son_kart, view=self)
            except discord.HTTPException:
                pass


# ── Oyun Akışı ────────────────────────────────────────────────────────────────

async def _oyunu_başlat(interaction: discord.Interaction, oyuncular: list[discord.Member]):
    random.shuffle(oyuncular)
    oyun = RusRuletiOyun(oyuncular)
    view = TetikView(oyun, interaction.channel)
    sıra = oyun.mevcut_oyuncu
    ihtimal = round(100 / oyun.kalan_oda)
    bar = c_progress(ihtimal, 100, length=14)

    card = c_container(
        c_section(
            c_text(f"## 🔫 Rus Ruleti — Başladı!\n### 🎯 İlk sıra: {sıra.mention}"),
            accessory=c_thumbnail(str(sıra.display_avatar.url)),
        ),
        c_separator(),
        c_text(
            f"**👥 Oyuncular:** `{len(oyuncular)}` kişi\n"
            f"**🎲 Silah:** 1 mermi · 6 oda\n\n"
            f"**🎯 Tehlike:** `{bar}` `%{ihtimal}`\n"
            f"**🔫 Silah:** {_ihtimal_bar(oyun.kalan_oda)}"
        ),
        c_separator(),
        c_text("**🪑 Sıralama:** " + " → ".join(o.mention for o in oyuncular)),
        color=COLORS.DANGER,
    )
    msg = await channel_send(interaction.channel, card, view=view)
    view.msg = msg


async def _sonraki_tur(interaction: discord.Interaction, oyun: RusRuletiOyun):
    view = TetikView(oyun, interaction.channel)
    msg  = await channel_send(interaction.channel, _tetik_card(oyun), view=view)
    view.msg = msg


async def _oyun_bitti(interaction: discord.Interaction, oyun: RusRuletiOyun, kurban: discord.Member):
    hayatta = [o for o in oyun.oyuncular if o.id != kurban.id]
    gif = await giphy("bang gunshot dead")

    hayatta_str = (
        "\n".join(f"🎉 {o.mention}" for o in hayatta) if hayatta else "_Kimse kalmadı._"
    )
    items: list[dict] = [
        c_section(
            c_text(f"## 💀 Oyun Bitti\n### Kurban: {kurban.mention}"),
            accessory=c_thumbnail(str(kurban.display_avatar.url)),
        ),
        c_separator(),
        c_text(f"**🏆 Hayatta Kalanlar**\n{hayatta_str}"),
    ]
    if gif:
        items.append(c_separator())
        items.append(c_media(gif))

    son_kart = (c_container(*items, color=COLORS.DANGER),)
    view = TekrarOynaView(oyun.oyuncular, kurban, son_kart)
    msg  = await channel_send(interaction.channel, *son_kart, view=view)
    view.msg = msg


# ── Cog ───────────────────────────────────────────────────────────────────────

class RusRuleti(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rusruleti", description="Rus Ruleti oyna! 6 oda, 1 mermi.")
    async def rusruleti(self, interaction: discord.Interaction):
        lobi = LobiView(interaction.user)
        lobi.msg = await respond(interaction, *lobi._card(), view=lobi)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await error_response(interaction, str(error))


async def setup(bot: commands.Bot):
    await bot.add_cog(RusRuleti(bot))
