import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from ._shared import giphy
from .._v2 import (
    c_text, c_thumbnail, c_section, c_container, c_separator, c_media,
    respond, update, channel_send, msg_edit,
)

KATEGORILER = ["İsim", "Şehir", "Hayvan", "Meyve/Sebze", "Ülke"]
HARFLER     = list("ABCDEFGHİKLMNOPRSTUYZ")
TOPLAM_TUR  = 5
TUR_SURESI  = 60
LOBI_SURESI = 60

_TR_NORM: dict[str, str] = {"I": "İ"}


def _normalize(s: str) -> str:
    return "".join(_TR_NORM.get(c, c) for c in s.upper().strip())


def _harf_eşleşir(kelime: str, harf: str) -> bool:
    if not kelime:
        return False
    return _normalize(kelime)[0] == _normalize(harf)


# ── Modal ────────────────────────────────────────────────────────────────────────

class IsimSehirModal(discord.ui.Modal):
    def __init__(self, oyun: "IsimSehirOyunu"):
        super().__init__(title=f"Tur {oyun.tur} — Harf: {oyun.harf}")
        self.oyun = oyun
        harf = oyun.harf

        self.isim   = discord.ui.TextInput(label="İsim",        placeholder=f"'{harf}' ile başlayan isim",        required=False, max_length=50)
        self.sehir  = discord.ui.TextInput(label="Şehir",       placeholder=f"'{harf}' ile başlayan şehir",       required=False, max_length=50)
        self.hayvan = discord.ui.TextInput(label="Hayvan",       placeholder=f"'{harf}' ile başlayan hayvan",      required=False, max_length=50)
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
            return await interaction.response.send_message("Bu oyunda değilsin!", ephemeral=True)
        if interaction.user.id in self.oyun.cevaplar:
            return await interaction.response.send_message("Zaten cevaplarını girdin!", ephemeral=True)
        await interaction.response.send_modal(IsimSehirModal(self.oyun))


# ── Lobi View ────────────────────────────────────────────────────────────────────

class IsimSehirLobiView(discord.ui.View):
    def __init__(self, kurucu: discord.Member):
        super().__init__(timeout=LOBI_SURESI)
        self.kurucu    = kurucu
        self.oyuncular: list[discord.Member] = [kurucu]
        self.msg: discord.Message | None = None
        self._başladı  = False

    def _card(self) -> tuple[dict, ...]:
        lines = (
            ["**📝 İsim Şehir — Lobi**", "",
             f"**{self.kurucu.mention}** bir oyun kurdu!",
             f"**Katılımcılar ({len(self.oyuncular)}):**"]
            + [f"• {o.mention}" for o in self.oyuncular]
            + ["", f"-# En az 2 oyuncu • {TOPLAM_TUR} tur • Her turda {TUR_SURESI}sn"]
        )
        return (c_container(c_text("\n".join(lines)), color=0x5865F2),)

    async def on_timeout(self):
        if not self._başladı:
            for c in self.children:
                c.disabled = True
            if self.msg:
                try:
                    lines_t = list(self._card()[0]["components"][0]["content"].splitlines())
                    lines_t.append("\n⏰ Lobi süresi doldu.")
                    timeout_card = c_container(c_text("\n".join(lines_t)), color=0x95A5A6)
                    await msg_edit(self.msg, timeout_card, view=self)
                except discord.HTTPException:
                    pass

    @discord.ui.button(label="Katıl", emoji="✋", style=discord.ButtonStyle.success)
    async def katıl_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user in self.oyuncular:
            return await interaction.response.send_message("Zaten katıldın!", ephemeral=True)
        if len(self.oyuncular) >= 8:
            return await interaction.response.send_message("Lobi dolu (maks 8)!", ephemeral=True)
        self.oyuncular.append(interaction.user)
        await interaction.response.defer()
        assert self.msg
        await msg_edit(self.msg, *self._card(), view=self)

    @discord.ui.button(label="Ayrıl", emoji="🚪", style=discord.ButtonStyle.secondary)
    async def ayrıl_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id == self.kurucu.id:
            return await interaction.response.send_message(
                "Kurucu ayrılamaz. Lobi kapatmak için **İptal** butonunu kullan.", ephemeral=True
            )
        if interaction.user not in self.oyuncular:
            return await interaction.response.send_message("Bu lobide değilsin!", ephemeral=True)
        self.oyuncular.remove(interaction.user)
        await interaction.response.defer()
        assert self.msg
        await msg_edit(self.msg, *self._card(), view=self)

    @discord.ui.button(label="Başlat", emoji="▶️", style=discord.ButtonStyle.primary)
    async def başlat_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.kurucu.id:
            return await interaction.response.send_message("Sadece kurucu başlatabilir!", ephemeral=True)
        if len(self.oyuncular) < 2:
            return await interaction.response.send_message("En az 2 oyuncu gerekli!", ephemeral=True)
        self._başladı = True
        self.stop()
        for c in self.children:
            c.disabled = True
        await interaction.response.defer()
        assert self.msg
        await msg_edit(self.msg, *self._card(), view=self)
        oyun = IsimSehirOyunu(list(self.oyuncular), interaction.channel)  # type: ignore[arg-type]
        await oyun.yeni_tur()

    @discord.ui.button(label="İptal", emoji="✖️", style=discord.ButtonStyle.danger)
    async def iptal_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.kurucu.id:
            return await interaction.response.send_message("Sadece kurucu iptal edebilir!", ephemeral=True)
        self._başladı = True
        self.stop()
        for c in self.children:
            c.disabled = True
        await update(interaction,
            c_container(c_text(f"**🚫 Lobi İptal Edildi**\n\n{interaction.user.mention} lobi iptal etti."), color=0x95A5A6),
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
            return await interaction.response.send_message("Bu oyuna dahil değildin!", ephemeral=True)
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
        lines = [
            f"**📝 İsim Şehir — Tur {self.tur}/{TOPLAM_TUR}**",
            "",
            f"**Bu turun harfi: `{self.harf}`**",
            "",
            f"Kategoriler: {', '.join(f'**{k}**' for k in KATEGORILER)}",
            "",
            f"✏️ **Cevaplarımı Gir** butonuna bas ve {TUR_SURESI} saniye içinde cevaplarını gönder!",
            "",
            f"👥 Cevaplayan: **{girenler}/{toplam}**",
            "",
            "-# Eşsiz cevap = 10 puan  •  Ortak cevap = 5 puan  •  Yanlış harf = 0 puan",
        ]
        return c_container(c_text("\n".join(lines)), color=0xF0A030)

    async def yeni_tur(self):
        self.harf     = random.choice(HARFLER)
        self.cevaplar = {}
        view = IsimSehirTurView(self)
        self.tur_view = view
        self.msg = await channel_send(self.kanal, self._tur_card(), view=view)

    async def cevap_kaydet(self, interaction: discord.Interaction, cevaplar: dict[str, str]):
        self.cevaplar[interaction.user.id] = cevaplar
        await interaction.response.send_message("✅ Cevapların kaydedildi!", ephemeral=True)

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

        result_lines = [f"**📊 Tur {self.tur} Sonuçları — Harf: `{self.harf}`**", ""]
        for oyuncu in self.oyuncular:
            uid  = oyuncu.id
            cvps = self.cevaplar.get(uid, {})
            pts  = tur_puanları.get(uid, {})
            result_lines.append(f"**{oyuncu.display_name}** — Toplam: {self.skorlar[uid]} puan")
            for kat in KATEGORILER:
                val  = cvps.get(kat, "—") or "—"
                puan = pts.get(kat, 0)
                result_lines.append(f"  **{kat}:** {val} `+{puan}`")
            result_lines.append("")

        await channel_send(self.kanal, c_container(c_text("\n".join(result_lines)), color=0x57F287))

        self.tur += 1
        if self.tur > TOPLAM_TUR:
            await self._oyun_bitti()
        else:
            await asyncio.sleep(4)
            await self.yeni_tur()

    async def _oyun_bitti(self):
        sıralama = sorted(self.oyuncular, key=lambda o: self.skorlar[o.id], reverse=True)
        madalya  = ["🥇", "🥈", "🥉"]
        satırlar = []
        for i, oyuncu in enumerate(sıralama):
            m = madalya[i] if i < 3 else f"`{i+1}.`"
            satırlar.append(f"{m} {oyuncu.mention} — **{self.skorlar[oyuncu.id]} puan**")

        gif = await giphy("trophy winner podium celebration")
        items: list[dict] = [c_text(f"**🏆 İsim Şehir Bitti!**\n\n" + "\n".join(satırlar) + f"\n\n-# {TOPLAM_TUR} tur oynadınız.")]
        if gif:
            items.append(c_separator())
            items.append(c_media(gif))
        son_kart = (c_container(*items, color=0xFEE75C),)

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
