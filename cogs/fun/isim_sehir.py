import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

# ── Sabitler ─────────────────────────────────────────────────────────────────────

KATEGORILER = ["İsim", "Şehir", "Hayvan", "Meyve/Sebze", "Ülke"]

HARFLER = list("ABCDEFGHİKLMNOPRSTUYZ")

TOPLAM_TUR  = 5
TUR_SURESI  = 60   # saniye
LOBI_SURESI = 60   # saniye

# Türkçe I/İ normalizasyonu
_TR_NORM: dict[str, str] = {"I": "İ"}


def _normalize(s: str) -> str:
    """Karşılaştırma için büyük harf + I→İ normalizasyonu."""
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
        self.oyun  = oyun
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
        self.kurucu   = kurucu
        self.oyuncular: list[discord.Member] = [kurucu]
        self.msg: discord.Message | None = None
        self._başladı  = False

    def _embed(self) -> discord.Embed:
        e = discord.Embed(
            title="📝 İsim Şehir — Lobi",
            description=(
                f"**{self.kurucu.mention}** bir oyun kurdu!\n\n"
                f"**Katılımcılar ({len(self.oyuncular)}):**\n"
                + "\n".join(f"• {o.mention}" for o in self.oyuncular)
            ),
            color=discord.Color.blurple(),
        )
        e.set_footer(text=f"En az 2 oyuncu • {TOPLAM_TUR} tur • Her turda {TUR_SURESI}sn")
        e.timestamp = discord.utils.utcnow()
        return e

    async def on_timeout(self):
        if not self._başladı:
            for c in self.children:
                c.disabled = True
            if self.msg:
                try:
                    e = self._embed()
                    e.description += "\n\n⏰ Lobi süresi doldu."
                    await self.msg.edit(embed=e, view=self)
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
        await self.msg.edit(embed=self._embed())

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
        await self.msg.edit(embed=self._embed())

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
        await self.msg.edit(embed=self._embed(), view=self)
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
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🚫 Lobi İptal Edildi",
                description=f"{interaction.user.mention} lobi iptal etti.",
                color=discord.Color.greyple(),
                timestamp=discord.utils.utcnow(),
            ),
            view=self,
        )


# ── Tekrar Oyna View ─────────────────────────────────────────────────────────────

class IsimSehirTekrarView(discord.ui.View):
    def __init__(self, oyuncular: list[discord.Member]):
        super().__init__(timeout=120)
        self.oyuncular = oyuncular
        self.msg: discord.Message | None = None

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await self.msg.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Tekrar Oyna", emoji="🔄", style=discord.ButtonStyle.success)
    async def tekrar(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyuncular:
            return await interaction.response.send_message("Bu oyuna dahil değildin!", ephemeral=True)
        btn.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)
        lobi = IsimSehirLobiView(interaction.user)
        msg  = await interaction.channel.send(embed=lobi._embed(), view=lobi)
        lobi.msg = msg


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

    def _tur_embed(self) -> discord.Embed:
        girenler = len(self.cevaplar)
        toplam   = len(self.oyuncular)
        e = discord.Embed(
            title=f"📝 İsim Şehir — Tur {self.tur}/{TOPLAM_TUR}",
            description=(
                f"**Bu turun harfi: `{self.harf}`**\n\n"
                f"Kategoriler: {', '.join(f'**{k}**' for k in KATEGORILER)}\n\n"
                f"✏️ **Cevaplarımı Gir** butonuna bas ve {TUR_SURESI} saniye içinde cevaplarını gönder!\n\n"
                f"👥 Cevaplayan: **{girenler}/{toplam}**"
            ),
            color=discord.Color.orange(),
        )
        e.set_footer(text="Eşsiz cevap = 10 puan  •  Ortak cevap = 5 puan  •  Yanlış harf = 0 puan")
        e.timestamp = discord.utils.utcnow()
        return e

    async def yeni_tur(self):
        self.harf     = random.choice(HARFLER)
        self.cevaplar = {}
        view = IsimSehirTurView(self)
        self.tur_view = view
        self.msg = await self.kanal.send(embed=self._tur_embed(), view=view)

    async def cevap_kaydet(self, interaction: discord.Interaction, cevaplar: dict[str, str]):
        self.cevaplar[interaction.user.id] = cevaplar
        await interaction.response.send_message("✅ Cevapların kaydedildi!", ephemeral=True)

        assert self.msg
        await self.msg.edit(embed=self._tur_embed())

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
        await self.msg.edit(view=self.tur_view)

        # ── Puan hesapla ────────────────────────────────────────────────────
        tur_puanları: dict[int, dict[str, int]] = {o.id: {} for o in self.oyuncular}

        for kategori in KATEGORILER:
            # Geçerli cevapları topla (doğru harfle başlayanlar)
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

        # ── Sonuç embed'i ────────────────────────────────────────────────────
        e = discord.Embed(
            title=f"📊 Tur {self.tur} Sonuçları — Harf: `{self.harf}`",
            color=discord.Color.green(),
        )
        for oyuncu in self.oyuncular:
            uid  = oyuncu.id
            cvps = self.cevaplar.get(uid, {})
            pts  = tur_puanları.get(uid, {})
            satirlar = []
            for kat in KATEGORILER:
                val  = cvps.get(kat, "—") or "—"
                puan = pts.get(kat, 0)
                satirlar.append(f"**{kat}:** {val} `+{puan}`")
            e.add_field(
                name=f"{oyuncu.display_name} | Toplam: {self.skorlar[uid]} puan",
                value="\n".join(satirlar),
                inline=False,
            )
        e.timestamp = discord.utils.utcnow()
        await self.kanal.send(embed=e)

        # ── Sonraki tur veya bitiş ────────────────────────────────────────────
        self.tur += 1
        if self.tur > TOPLAM_TUR:
            await self._oyun_bitti()
        else:
            await asyncio.sleep(4)
            await self.yeni_tur()

    async def _oyun_bitti(self):
        sıralama = sorted(self.oyuncular, key=lambda o: self.skorlar[o.id], reverse=True)
        satirlar = []
        madalya  = ["🥇", "🥈", "🥉"]
        for i, oyuncu in enumerate(sıralama):
            m = madalya[i] if i < 3 else f"`{i+1}.`"
            satirlar.append(f"{m} {oyuncu.mention} — **{self.skorlar[oyuncu.id]} puan**")

        e = discord.Embed(
            title="🏆 İsim Şehir Bitti!",
            description="\n".join(satirlar),
            color=discord.Color.gold(),
        )
        e.set_footer(text=f"{TOPLAM_TUR} tur oynadınız.")
        e.timestamp = discord.utils.utcnow()
        tekrar = IsimSehirTekrarView(self.oyuncular)
        msg    = await self.kanal.send(embed=e, view=tekrar)
        tekrar.msg = msg


# ── Cog ──────────────────────────────────────────────────────────────────────────

class IsimSehir(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="isimşehir", description="Arkadaşlarla İsim Şehir oyna! (5 tur, 5 kategori)")
    async def isim_sehir(self, interaction: discord.Interaction):
        view = IsimSehirLobiView(interaction.user)
        await interaction.response.send_message(embed=view._embed(), view=view)
        view.msg = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(IsimSehir(bot))
