import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from ._shared import giphy
from .._v2 import (
    COLORS, c_card, c_text, c_thumbnail, c_section, c_container, c_separator, c_media,
    c_progress, respond, update, channel_send, msg_edit, followup as v2_followup,
)

KATEGORILER = ["İsim", "Şehir", "Hayvan", "Meyve/Sebze", "Ülke"]
KATEGORI_EMOJI = {
    "İsim": "👤",
    "Şehir": "🏙️",
    "Hayvan": "🐾",
    "Meyve/Sebze": "🍎",
    "Ülke": "🌍",
}
HARFLER     = list("ABCDEFGHİKLMNOPRSTUYZ")
TOPLAM_TUR  = 5
TUR_SURESI  = 60
LOBI_SURESI = 60
MAX_OYUNCU  = 8

_TR_NORM: dict[str, str] = {"I": "İ"}


def _normalize(s: str) -> str:
    return "".join(_TR_NORM.get(c, c) for c in s.upper().strip())


def _harf_eşleşir(kelime: str, harf: str) -> bool:
    if not kelime:
        return False
    return _normalize(kelime)[0] == _normalize(harf)


async def _v2_err(interaction: discord.Interaction, title: str, body: str = "", color: int = COLORS.DANGER):
    thumb = str(interaction.client.user.display_avatar.url)
    if interaction.response.is_done():
        await v2_followup(interaction, c_card(f"## {title}", body=body, thumbnail=thumb, color=color), ephemeral=True)
    else:
        await respond(interaction, c_card(f"## {title}", body=body, thumbnail=thumb, color=color), ephemeral=True)


# ── Modal ────────────────────────────────────────────────────────────────────────

class IsimSehirModal(discord.ui.Modal):
    def __init__(self, oyun: "IsimSehirOyunu"):
        super().__init__(title=f"Tur {oyun.tur} — Harf: {oyun.harf}")
        self.oyun = oyun
        harf = oyun.harf

        self.isim   = discord.ui.TextInput(label="İsim",        placeholder=f"'{harf}' ile başlayan isim",        required=False, max_length=50)
        self.sehir  = discord.ui.TextInput(label="Şehir",       placeholder=f"'{harf}' ile başlayan şehir",       required=False, max_length=50)
        self.hayvan = discord.ui.TextInput(label="Hayvan",      placeholder=f"'{harf}' ile başlayan hayvan",      required=False, max_length=50)
        self.meyve  = discord.ui.TextInput(label="Meyve/Sebze", placeholder=f"'{harf}' ile başlayan meyve/sebze", required=False, max_length=50)
        self.ulke   = discord.ui.TextInput(label="Ülke",        placeholder=f"'{harf}' ile başlayan ülke",        required=False, max_length=50)

        for item in (self.isim, self.sehir, self.hayvan, self.meyve, self.ulke):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        cevaplar = {
            "İsim":        self.isim.value.strip(),
            "Şehir":       self.sehir.value.strip(),
            "Hayvan":      self.hayvan.value.strip(),
            "Meyve/Sebze": self.meyve.value.strip(),
            "Ülke":        self.ulke.value.strip(),
        }
        await self.oyun.cevap_kaydet(interaction, cevaplar)


# ── Tur View ─────────────────────────────────────────────────────────────────────

class IsimSehirTurView(discord.ui.View):
    def __init__(self, oyun: "IsimSehirOyunu"):
        super().__init__(timeout=TUR_SURESI)
        self.oyun   = oyun
        self._bitti = False

    async def on_timeout(self):
        if not self._bitti:
            self._bitti = True
            await self.oyun.tur_bitti()

    @discord.ui.button(label="Cevaplarımı Gir", emoji="✏️", style=discord.ButtonStyle.primary)
    async def cevap_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyun.oyuncular:
            return await _v2_err(interaction, "⛔ Erişim", "Bu oyuna dahil değilsin.")
        if interaction.user.id in self.oyun.cevaplar:
            return await _v2_err(interaction, "🔁 Zaten Girildi", "Cevaplarını zaten gönderdin.", COLORS.WARNING)
        await interaction.response.send_modal(IsimSehirModal(self.oyun))


# ── Lobi View ────────────────────────────────────────────────────────────────────

class IsimSehirLobiView(discord.ui.View):
    def __init__(self, kurucu: discord.Member):
        super().__init__(timeout=LOBI_SURESI)
        self.kurucu    = kurucu
        self.oyuncular: list[discord.Member] = [kurucu]
        self.msg: discord.Message | None = None
        self._başladı  = False

    def _card(self, *, kapanis: str | None = None, color: int = COLORS.PRIMARY) -> tuple[dict, ...]:
        bar = c_progress(len(self.oyuncular), MAX_OYUNCU, length=12)
        oyuncu_listesi = "\n".join(f"🪑 {o.mention}" for o in self.oyuncular)

        items: list[dict] = [
            c_section(
                c_text("## 📝 İsim Şehir — Lobi"),
                accessory=c_thumbnail(str(self.kurucu.display_avatar.url)),
            ),
            c_separator(),
            c_text(
                f"`{bar}` `{len(self.oyuncular)}/{MAX_OYUNCU}` oyuncu\n\n"
                f"{oyuncu_listesi}"
            ),
            c_separator(),
            c_text(
                f"**📐 Kurallar**\n"
                f"┗ {TOPLAM_TUR} tur · {len(KATEGORILER)} kategori · Tur süresi `{TUR_SURESI}` sn\n"
                f"┗ Eşsiz cevap **10 puan**, ortak cevap **5 puan**"
            ),
        ]
        if kapanis:
            items.append(c_separator())
            items.append(c_text(kapanis))
        else:
            items.append(c_separator())
            items.append(c_text(f"-# 👑 Kurucu: {self.kurucu.mention} · ⏱️ Lobi: {LOBI_SURESI}sn"))
        return (c_container(*items, color=color),)

    async def on_timeout(self):
        if not self._başladı:
            for c in self.children:
                c.disabled = True
            if self.msg:
                try:
                    await msg_edit(self.msg, *self._card(kapanis="⏰ **Lobi süresi doldu.**", color=0x95A5A6), view=self)
                except discord.HTTPException:
                    pass

    @discord.ui.button(label="Katıl", emoji="✋", style=discord.ButtonStyle.success)
    async def katıl_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user in self.oyuncular:
            return await _v2_err(interaction, "⚠️ Zaten Lobide", "Lobiye zaten katıldın.", COLORS.WARNING)
        if len(self.oyuncular) >= MAX_OYUNCU:
            return await _v2_err(interaction, "🚫 Lobi Dolu", f"Maksimum `{MAX_OYUNCU}` oyuncu.")
        self.oyuncular.append(interaction.user)
        await interaction.response.defer()
        assert self.msg
        await msg_edit(self.msg, *self._card(), view=self)

    @discord.ui.button(label="Ayrıl", emoji="🚪", style=discord.ButtonStyle.secondary)
    async def ayrıl_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id == self.kurucu.id:
            return await _v2_err(interaction, "👑 Kurucu Ayrılamaz", "Lobiyi kapatmak için **İptal** butonunu kullan.", COLORS.WARNING)
        if interaction.user not in self.oyuncular:
            return await _v2_err(interaction, "❌ Lobide Değilsin", "Bu lobiye dahil değilsin.")
        self.oyuncular.remove(interaction.user)
        await interaction.response.defer()
        assert self.msg
        await msg_edit(self.msg, *self._card(), view=self)

    @discord.ui.button(label="Başlat", emoji="▶️", style=discord.ButtonStyle.primary)
    async def başlat_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.kurucu.id:
            return await _v2_err(interaction, "🚫 Yetki Yok", "Sadece **kurucu** başlatabilir.")
        if len(self.oyuncular) < 2:
            return await _v2_err(interaction, "⚠️ Yetersiz Oyuncu", "En az **2 oyuncu** gerekli.", COLORS.WARNING)
        self._başladı = True
        self.stop()
        for c in self.children:
            c.disabled = True
        await interaction.response.defer()
        assert self.msg
        await msg_edit(self.msg, *self._card(kapanis="▶️ **Oyun başlıyor...**", color=COLORS.SUCCESS), view=self)
        oyun = IsimSehirOyunu(list(self.oyuncular), interaction.channel)  # type: ignore[arg-type]
        await oyun.yeni_tur()

    @discord.ui.button(label="İptal", emoji="✖️", style=discord.ButtonStyle.danger)
    async def iptal_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.kurucu.id:
            return await _v2_err(interaction, "🚫 Yetki Yok", "Sadece **kurucu** iptal edebilir.")
        self._başladı = True
        self.stop()
        for c in self.children:
            c.disabled = True
        await update(interaction,
            c_card("## 🚫 Lobi İptal Edildi", body=f"{interaction.user.mention} lobi iptal etti.", color=0x95A5A6),
            view=self,
        )


# ── Tekrar Oyna View ─────────────────────────────────────────────────────────────

class IsimSehirTekrarView(discord.ui.View):
    def __init__(self, oyuncular: list[discord.Member], son_kart: tuple[dict, ...]):
        super().__init__(timeout=120)
        self.oyuncular = oyuncular
        self.son_kart  = son_kart
        self.msg: discord.Message | None = None

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await msg_edit(self.msg, *self.son_kart, view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Tekrar Oyna", emoji="🔄", style=discord.ButtonStyle.success)
    async def tekrar(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyuncular:
            return await _v2_err(interaction, "⛔ Erişim", "Bu oyuna dahil değildin.")
        btn.disabled = True
        self.stop()
        await update(interaction, *self.son_kart, view=self)
        lobi = IsimSehirLobiView(interaction.user)
        new_msg = await channel_send(interaction.channel, *lobi._card(), view=lobi)
        lobi.msg = new_msg


# ── Oyun Motoru ──────────────────────────────────────────────────────────────────

class IsimSehirOyunu:
    def __init__(self, oyuncular: list[discord.Member], kanal: discord.TextChannel):
        self.oyuncular = oyuncular
        self.kanal     = kanal
        self.tur       = 1
        self.harf: str = ""
        self.cevaplar: dict[int, dict[str, str]] = {}
        self.skorlar: dict[int, int] = {o.id: 0 for o in oyuncular}
        self.tur_view: IsimSehirTurView | None = None
        self.msg: discord.Message | None = None

    def _tur_card(self) -> dict:
        girenler = len(self.cevaplar)
        toplam   = len(self.oyuncular)
        progress = c_progress(girenler, toplam, length=14)

        kategori_satırları = "\n".join(f"{KATEGORI_EMOJI[k]} **{k}**" for k in KATEGORILER)

        return c_container(
            c_section(
                c_text(f"## 📝 İsim Şehir\n### Tur {self.tur}/{TOPLAM_TUR} · Harf: `{self.harf}`"),
                accessory=c_thumbnail(str(self.oyuncular[0].guild.icon.url) if self.oyuncular[0].guild and self.oyuncular[0].guild.icon else str(self.oyuncular[0].display_avatar.url)),
            ),
            c_separator(),
            c_text(f"**📋 Kategoriler**\n{kategori_satırları}"),
            c_separator(),
            c_text(
                f"**👥 Cevaplayanlar**\n"
                f"`{progress}` `{girenler}/{toplam}`"
            ),
            c_separator(),
            c_text(f"-# ✏️ **Cevaplarımı Gir** butonuna bas · ⏱️ {TUR_SURESI}sn · 🎯 Eşsiz=10p, Ortak=5p"),
            color=0xF0A030,
        )

    async def yeni_tur(self):
        self.harf     = random.choice(HARFLER)
        self.cevaplar = {}
        view = IsimSehirTurView(self)
        self.tur_view = view
        self.msg = await channel_send(self.kanal, self._tur_card(), view=view)

    async def cevap_kaydet(self, interaction: discord.Interaction, cevaplar: dict[str, str]):
        self.cevaplar[interaction.user.id] = cevaplar
        thumb = str(interaction.user.display_avatar.url)
        cevap_satırları = "\n".join(
            f"{KATEGORI_EMOJI[k]} **{k}:** `{cevaplar.get(k) or '—'}`"
            for k in KATEGORILER
        )
        await respond(interaction,
            c_card(
                "## ✅ Cevaplar Kaydedildi",
                body=cevap_satırları,
                thumbnail=thumb,
                color=COLORS.SUCCESS,
            ),
            ephemeral=True,
        )

        assert self.msg
        await msg_edit(self.msg, self._tur_card(), view=self.tur_view)

        if len(self.cevaplar) >= len(self.oyuncular):
            assert self.tur_view
            if not self.tur_view._bitti:
                self.tur_view._bitti = True
                self.tur_view.stop()
                await self.tur_bitti()

    async def tur_bitti(self):
        assert self.tur_view and self.msg
        for c in self.tur_view.children:
            c.disabled = True
        await msg_edit(self.msg, self._tur_card(), view=self.tur_view)

        tur_puanları: dict[int, dict[str, int]] = {o.id: {} for o in self.oyuncular}

        for kategori in KATEGORILER:
            geçerli: dict[str, list[int]] = {}
            for uid, cvplar in self.cevaplar.items():
                val = cvplar.get(kategori, "").strip()
                if _harf_eşleşir(val, self.harf):
                    norm = _normalize(val)
                    geçerli.setdefault(norm, []).append(uid)

            for norm, uid_list in geçerli.items():
                puan = 10 if len(uid_list) == 1 else 5
                for uid in uid_list:
                    tur_puanları[uid][kategori] = puan
                    self.skorlar[uid] += puan

        # Sıralama (bu tur için skor)
        sıralı = sorted(self.oyuncular, key=lambda o: -self.skorlar[o.id])

        oyuncu_blokları: list[str] = []
        for i, oyuncu in enumerate(sıralı):
            uid  = oyuncu.id
            cvps = self.cevaplar.get(uid, {})
            pts  = tur_puanları.get(uid, {})
            tur_toplam = sum(pts.values())
            rank = ["🥇", "🥈", "🥉"][i] if i < 3 else f"`#{i+1}`"

            satırlar = [f"{rank} **{oyuncu.display_name}** — Genel: `{self.skorlar[uid]}` (`+{tur_toplam}` bu tur)"]
            for kat in KATEGORILER:
                val = cvps.get(kat, "—") or "—"
                puan = pts.get(kat, 0)
                emoji = KATEGORI_EMOJI[kat]
                puan_str = f"`+{puan}`" if puan else "`0`"
                satırlar.append(f"┗ {emoji} **{kat}:** {val} {puan_str}")
            oyuncu_blokları.append("\n".join(satırlar))

        result_card = c_container(
            c_text(f"## 📊 Tur {self.tur} Sonuçları\n-# Harf: `{self.harf}`"),
            c_separator(),
            c_text("\n\n".join(oyuncu_blokları)),
            color=COLORS.SUCCESS,
        )
        await channel_send(self.kanal, result_card)

        self.tur += 1
        if self.tur > TOPLAM_TUR:
            await self._oyun_bitti()
        else:
            await asyncio.sleep(4)
            await self.yeni_tur()

    async def _oyun_bitti(self):
        sıralama = sorted(self.oyuncular, key=lambda o: self.skorlar[o.id], reverse=True)
        madalya  = ["🥇", "🥈", "🥉"]

        max_skor = self.skorlar[sıralama[0].id] if sıralama else 1
        satırlar = []
        for i, oyuncu in enumerate(sıralama):
            m = madalya[i] if i < 3 else f"`#{i+1}`"
            puan = self.skorlar[oyuncu.id]
            bar = c_progress(puan, max(max_skor, 1), length=12)
            satırlar.append(f"{m} {oyuncu.mention}\n┗ `{bar}` **{puan}** puan")

        kazanan = sıralama[0] if sıralama else None
        gif = await giphy("trophy winner podium celebration")

        items: list[dict] = [
            c_section(
                c_text(f"## 🏆 İsim Şehir Bitti!\n### {kazanan.display_name if kazanan else '—'} kazandı"),
                accessory=c_thumbnail(str(kazanan.display_avatar.url) if kazanan else ""),
            ),
            c_separator(),
            c_text("\n\n".join(satırlar)),
            c_separator(),
            c_text(f"-# 🎯 {TOPLAM_TUR} tur · {len(self.oyuncular)} oyuncu"),
        ]
        if gif:
            items.append(c_separator())
            items.append(c_media(gif))

        son_kart = (c_container(*items, color=COLORS.GAME),)
        tekrar = IsimSehirTekrarView(self.oyuncular, son_kart)
        msg    = await channel_send(self.kanal, *son_kart, view=tekrar)
        tekrar.msg = msg


# ── Cog ──────────────────────────────────────────────────────────────────────────

class IsimSehir(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="isimşehir", description="Arkadaşlarla İsim Şehir oyna! (5 tur, 5 kategori)")
    async def isim_sehir(self, interaction: discord.Interaction):
        view = IsimSehirLobiView(interaction.user)  # type: ignore[arg-type]
        view.msg = await respond(interaction, *view._card(), view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(IsimSehir(bot))
