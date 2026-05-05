import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from collections import Counter
from ._shared import giphy

# ── Sabitler ──────────────────────────────────────────────────────────────────

LOBI_SURESI   = 120
GECE_SURESI   = 90
GUNDUZ_SURESI = 120
AVCI_SURESI   = 30
MIN_OYUNCU    = 4
MAX_OYUNCU    = 12

ROL_EMOJI = {
    "vampir": "🧛",
    "köylü":  "👨‍🌾",
    "doktor": "👨‍⚕️",
    "avcı":   "🏹",
    "kahin":  "🔮",
}

ROL_TANIM = {
    "vampir": "Her gece bir köylüyü öldürebilirsin. Vampir arkadaşlarını tanırsın!",
    "köylü":  "Gündüzleri oylama yaparak vampirleri bulmaya çalış.",
    "doktor": "Her gece bir oyuncuyu koruyabilirsin. Vampir o kişiyi seçerse ölmez!",
    "avcı":   "Öldürülürsen, son nefesinde bir kişiyi seç ve onu yanında götür!",
    "kahin":  "Her gece bir oyuncunun rolünü öğrenebilirsin. Bu bilgiyi akıllıca kullan!",
}

_ROL_SIRA = ["vampir", "köylü", "doktor", "avcı", "kahin"]


def _rol_dagit(n: int) -> list[str]:
    if n <= 4:
        return ["vampir", "köylü", "köylü", "köylü"]
    elif n == 5:
        return ["vampir", "doktor", "köylü", "köylü", "köylü"]
    elif n == 6:
        return ["vampir", "vampir", "doktor", "köylü", "köylü", "köylü"]
    elif n == 7:
        return ["vampir", "vampir", "doktor", "köylü", "köylü", "köylü", "köylü"]
    elif n == 8:
        return ["vampir", "vampir", "kahin", "doktor", "avcı", "köylü", "köylü", "köylü"]
    elif n == 9:
        return ["vampir", "vampir", "kahin", "doktor", "avcı", "köylü", "köylü", "köylü", "köylü"]
    elif n == 10:
        return ["vampir", "vampir", "vampir", "kahin", "doktor", "avcı", "köylü", "köylü", "köylü", "köylü"]
    elif n == 11:
        return ["vampir", "vampir", "vampir", "kahin", "doktor", "avcı", "köylü", "köylü", "köylü", "köylü", "köylü"]
    else:
        return ["vampir", "vampir", "vampir", "kahin", "doktor", "avcı",
                "köylü", "köylü", "köylü", "köylü", "köylü", "köylü"]


# ── Gece Aksiyon View (Ephemeral) ─────────────────────────────────────────────

class GeceAksiyonView(discord.ui.View):
    def __init__(self, oyun: "VampirKoyluOyunu", oyuncu: discord.Member, rol: str):
        super().__init__(timeout=GECE_SURESI)
        self.oyun       = oyun
        self.oyuncu     = oyuncu
        self.rol        = rol
        self.tamamlandı = False
        self._vampir_bilgi = ""
        self._build_select()

    def _build_select(self):
        oyun = self.oyun
        rol  = self.rol

        if rol == "vampir":
            diğer = [o for o in oyun.yaşayanlar if oyun.roller[o.id] == "vampir" and o.id != self.oyuncu.id]
            if diğer:
                oy_satırları = []
                for d in diğer:
                    if d.id in oyun.vampir_oyları:
                        hedef = next((o for o in oyun.oyuncular if o.id == oyun.vampir_oyları[d.id]), None)
                        oy_satırları.append(f"  • {d.display_name} → 💀 **{hedef.display_name if hedef else '?'}**")
                    else:
                        oy_satırları.append(f"  • {d.display_name} → ⏳ henüz seçmedi")
                takım_bilgi = "\n".join(oy_satırları)
                self._vampir_bilgi = f"\n\n🧛 **Vampir Takımın:**\n{takım_bilgi}"
            else:
                self._vampir_bilgi = "\n\n🧛 Sen tek vampirsin!"
            hedefler = [o for o in oyun.yaşayanlar if oyun.roller[o.id] != "vampir"]
            opts = [discord.SelectOption(label=o.display_name, value=str(o.id), emoji="💀") for o in hedefler]
            sel = discord.ui.Select(placeholder="🧛 Kurbanını seç...", options=opts)
            sel.callback = self._vampir_cb

        elif rol == "doktor":
            hedefler = oyun.yaşayanlar
            opts = [discord.SelectOption(label=o.display_name, value=str(o.id), emoji="💉") for o in hedefler]
            sel = discord.ui.Select(placeholder="👨‍⚕️ Koruyacağın kişiyi seç...", options=opts)
            sel.callback = self._doktor_cb

        else:  # kahin
            hedefler = [o for o in oyun.yaşayanlar if o.id != self.oyuncu.id]
            opts = [discord.SelectOption(label=o.display_name, value=str(o.id), emoji="👁️") for o in hedefler]
            sel = discord.ui.Select(placeholder="🔮 Rolünü öğrenmek istediğin kişiyi seç...", options=opts)
            sel.callback = self._kahin_cb

        self.add_item(sel)

    def _bul(self, uid: int) -> discord.Member | None:
        return next((o for o in self.oyun.oyuncular if o.id == uid), None)

    def _disable_all(self):
        for c in self.children:
            c.disabled = True

    async def _vampir_cb(self, interaction: discord.Interaction):
        if self.tamamlandı:
            return await interaction.response.defer()
        self.tamamlandı = True
        hedef_id = int(self.children[0].values[0])
        self.oyun.vampir_oyları[self.oyuncu.id] = hedef_id
        self.oyun.gece_tamamlayanlar.add(self.oyuncu.id)
        self._disable_all()
        hedef = self._bul(hedef_id)
        await interaction.response.edit_message(
            content=f"🧛 **{hedef.display_name if hedef else '?'}** seçildi. Sabahı bekle...",
            view=self,
        )
        await self.oyun._gece_eylem_kontrol()

    async def _doktor_cb(self, interaction: discord.Interaction):
        if self.tamamlandı:
            return await interaction.response.defer()
        self.tamamlandı = True
        hedef_id = int(self.children[0].values[0])
        self.oyun.doktor_koruması = hedef_id
        self.oyun.gece_tamamlayanlar.add(self.oyuncu.id)
        self._disable_all()
        hedef = self._bul(hedef_id)
        await interaction.response.edit_message(
            content=f"💉 **{hedef.display_name if hedef else '?'}** bu gece korunuyor. Sabahı bekle...",
            view=self,
        )
        await self.oyun._gece_eylem_kontrol()

    async def _kahin_cb(self, interaction: discord.Interaction):
        if self.tamamlandı:
            return await interaction.response.defer()
        self.tamamlandı = True
        hedef_id  = int(self.children[0].values[0])
        hedef_rol = self.oyun.roller.get(hedef_id, "köylü")
        self.oyun.kahin_görevi = hedef_id
        self.oyun.gece_tamamlayanlar.add(self.oyuncu.id)
        self._disable_all()
        hedef = self._bul(hedef_id)
        await interaction.response.edit_message(
            content=(
                f"🔮 **{hedef.display_name if hedef else '?'}** → "
                f"{ROL_EMOJI.get(hedef_rol, '❓')} **{hedef_rol.capitalize()}**\n\n"
                "Bu bilgiyi akıllıca kullan!"
            ),
            view=self,
        )
        await self.oyun._gece_eylem_kontrol()


# ── Gece View (Kanalda) ───────────────────────────────────────────────────────

class GeceView(discord.ui.View):
    def __init__(self, oyun: "VampirKoyluOyunu"):
        super().__init__(timeout=GECE_SURESI)
        self.oyun   = oyun
        self._bitti = False
        self.msg: discord.Message | None = None

    async def on_timeout(self):
        if not self._bitti:
            self._bitti = True
            self.stop()
            for c in self.children:
                c.disabled = True
            if self.msg:
                try:
                    await self.msg.edit(view=self)
                except discord.HTTPException:
                    pass
            await self.oyun._gece_coz()

    @discord.ui.button(label="Gece Eylemini Seç", emoji="🌙", style=discord.ButtonStyle.danger)
    async def eylem_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid  = interaction.user.id
        oyun = self.oyun

        if interaction.user not in oyun.yaşayanlar:
            return await interaction.response.send_message("Bu oyunda değilsin veya elendin!", ephemeral=True)
        if uid in oyun.gece_tamamlayanlar:
            return await interaction.response.send_message("Gece eylemini zaten tamamladın!", ephemeral=True)

        rol = oyun.roller.get(uid)
        if rol not in ("vampir", "doktor", "kahin"):
            return await interaction.response.send_message(
                "🌙 Sen köylüsün, bu gece yapacak bir eylemin yok. Uy ve sabahı bekle! 💤",
                ephemeral=True,
            )

        view = GeceAksiyonView(oyun, interaction.user, rol)
        await interaction.response.send_message(
            f"{ROL_EMOJI[rol]} **{rol.capitalize()}** rolündesin!{view._vampir_bilgi}\n\nGece eylemini seç:",
            view=view,
            ephemeral=True,
        )


# ── Gündüz Oylama View ────────────────────────────────────────────────────────

class GunduzOyView(discord.ui.View):
    def __init__(self, oyun: "VampirKoyluOyunu"):
        super().__init__(timeout=GUNDUZ_SURESI)
        self.oyun   = oyun
        self._bitti = False
        self.msg: discord.Message | None = None
        self._build_select()

    def _build_select(self):
        opts = [
            discord.SelectOption(label=o.display_name, value=str(o.id))
            for o in self.oyun.yaşayanlar
        ]
        sel = discord.ui.Select(placeholder="👆 İdam için oyladığın kişiyi seç...", options=opts)
        sel.callback = self._oy_cb
        self.add_item(sel)

    async def _oy_cb(self, interaction: discord.Interaction):
        uid  = interaction.user.id
        oyun = self.oyun

        if interaction.user not in oyun.yaşayanlar:
            return await interaction.response.send_message("Elendin, oy kullanamazsın!", ephemeral=True)
        if uid in oyun.gunduz_tamamlayanlar:
            return await interaction.response.send_message("Zaten oy kullandın!", ephemeral=True)

        hedef_id = int(self.children[0].values[0])
        if hedef_id == uid:
            return await interaction.response.send_message("Kendine oy veremezsin!", ephemeral=True)

        oyun.gunduz_oyları[uid] = hedef_id
        oyun.gunduz_tamamlayanlar.add(uid)

        hedef = next((o for o in oyun.yaşayanlar if o.id == hedef_id), None)
        await interaction.response.send_message(
            f"✅ **{hedef.display_name if hedef else '?'}** için oy kullandın!",
            ephemeral=True,
        )

        oy_sayısı = len(oyun.gunduz_oyları)
        toplam    = len(oyun.yaşayanlar)
        if self.msg:
            try:
                emb = self.msg.embeds[0].copy()
                emb.set_footer(text=f"✅ {oy_sayısı}/{toplam} oy kullandı")
                await self.msg.edit(embed=emb)
            except discord.HTTPException:
                pass

        if oy_sayısı >= toplam and not self._bitti:
            self._bitti = True
            self.stop()
            await oyun._gunduz_coz()

    async def on_timeout(self):
        if not self._bitti:
            self._bitti = True
            self.stop()
            for c in self.children:
                c.disabled = True
            if self.msg:
                try:
                    await self.msg.edit(view=self)
                except discord.HTTPException:
                    pass
            await self.oyun._gunduz_coz()


# ── Avcı Son Hamle View ───────────────────────────────────────────────────────

class AvcıSonHamleView(discord.ui.View):
    def __init__(self, oyun: "VampirKoyluOyunu", avcı: discord.Member):
        super().__init__(timeout=AVCI_SURESI)
        self.oyun   = oyun
        self.avcı   = avcı
        self._bitti = False
        self.msg: discord.Message | None = None
        opts = [
            discord.SelectOption(label=o.display_name, value=str(o.id))
            for o in oyun.yaşayanlar
        ]
        sel = discord.ui.Select(placeholder="🏹 Son okunu kime atıyorsun?", options=opts)
        sel.callback = self._atış_cb
        self.add_item(sel)

    async def _atış_cb(self, interaction: discord.Interaction):
        if interaction.user.id != self.avcı.id:
            return await interaction.response.send_message(
                "Bu sadece Avcının kullanabileceği bir menü!", ephemeral=True
            )
        if self._bitti:
            return await interaction.response.defer()
        self._bitti = True
        self.oyun._avci_hedef = int(self.children[0].values[0])
        self.oyun._avci_event.set()
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(view=self)

    async def on_timeout(self):
        if not self._bitti:
            self._bitti = True
            self.oyun._avci_event.set()
            for c in self.children:
                c.disabled = True
            if self.msg:
                try:
                    await self.msg.edit(view=self)
                except discord.HTTPException:
                    pass


# ── Tekrar Oyna View ──────────────────────────────────────────────────────────

class VampirTekrarView(discord.ui.View):
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
    async def tekrar_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyuncular:
            return await interaction.response.send_message(
                "Bu oyuna dahil değildin!", ephemeral=True
            )
        btn.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)
        lobi = VampirKoyluLobiView(interaction.user)
        msg  = await interaction.channel.send(embed=lobi._embed(), view=lobi)
        lobi.msg = msg


# ── Lobi View ─────────────────────────────────────────────────────────────────

class VampirKoyluLobiView(discord.ui.View):
    def __init__(self, kurucu: discord.Member):
        super().__init__(timeout=LOBI_SURESI)
        self.kurucu    = kurucu
        self.oyuncular: list[discord.Member] = [kurucu]
        self.msg: discord.Message | None = None
        self._başladı  = False

    def _embed(self) -> discord.Embed:
        dagılım  = _rol_dagit(len(self.oyuncular))
        sayım    = Counter(dagılım)
        rol_satır = "\n".join(
            f"{ROL_EMOJI[r]} {r.capitalize()}: {sayım[r]}"
            for r in _ROL_SIRA if r in sayım
        )
        e = discord.Embed(
            title="🧛 Vampir Köylü — Lobi",
            description=(
                f"**{self.kurucu.mention}** bir oyun kurdu!\n\n"
                f"**Katılımcılar ({len(self.oyuncular)}/{MAX_OYUNCU}):**\n"
                + "\n".join(f"• {o.mention}" for o in self.oyuncular)
            ),
            color=discord.Color.dark_red(),
        )
        e.add_field(
            name=f"Bu sayıyla rol dağılımı ({len(self.oyuncular)} kişi)",
            value=rol_satır,
            inline=False,
        )
        e.set_footer(text=f"Min {MIN_OYUNCU} • Max {MAX_OYUNCU} oyuncu • Kurucu başlatır")
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
        if len(self.oyuncular) >= MAX_OYUNCU:
            return await interaction.response.send_message("Lobi dolu (maks 12)!", ephemeral=True)
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
        if len(self.oyuncular) < MIN_OYUNCU:
            return await interaction.response.send_message(
                f"En az {MIN_OYUNCU} oyuncu gerekli! Şu an: {len(self.oyuncular)}", ephemeral=True
            )
        self._başladı = True
        self.stop()
        for c in self.children:
            c.disabled = True
        await interaction.response.defer()
        assert self.msg
        await self.msg.edit(embed=self._embed(), view=self)
        oyun = VampirKoyluOyunu(list(self.oyuncular), interaction.channel, self.kurucu)  # type: ignore[arg-type]
        await oyun.başlat()

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


# ── Oyun Motoru ───────────────────────────────────────────────────────────────

class VampirKoyluOyunu:
    def __init__(
        self,
        oyuncular: list[discord.Member],
        kanal: discord.TextChannel,
        kurucu: discord.Member,
    ):
        self.oyuncular  = oyuncular[:]
        self.yaşayanlar = oyuncular[:]
        self.kanal      = kanal
        self.kurucu     = kurucu
        self.roller: dict[int, str] = {}
        self.gece_sayısı = 0

        # Night state
        self.vampir_oyları: dict[int, int] = {}
        self.doktor_koruması: int | None   = None
        self.kahin_görevi: int | None      = None
        self.gece_tamamlayanlar: set[int]  = set()
        self._gece_cozuluyor = False

        # Day state
        self.gunduz_oyları: dict[int, int]  = {}
        self.gunduz_tamamlayanlar: set[int] = set()

        # Hunter
        self._avci_event = asyncio.Event()
        self._avci_hedef: int | None = None

        # Active views / messages
        self.aktif_gece_view: GeceView | None       = None
        self.aktif_gunduz_view: GunduzOyView | None = None
        self.gece_mesaj: discord.Message | None     = None
        self.gunduz_mesaj: discord.Message | None   = None

    # ── Yardımcılar ───────────────────────────────────────────────────────────

    def _bul(self, uid: int) -> discord.Member | None:
        return next((o for o in self.oyuncular if o.id == uid), None)

    def _beklenen_gece_aktörler(self) -> set[int]:
        return {o.id for o in self.yaşayanlar if self.roller[o.id] in ("vampir", "doktor", "kahin")}

    def _vampir_sayısı(self) -> int:
        return sum(1 for o in self.yaşayanlar if self.roller[o.id] == "vampir")

    def _köylü_sayısı(self) -> int:
        return sum(1 for o in self.yaşayanlar if self.roller[o.id] != "vampir")

    # ── Kazanma Kontrolü ──────────────────────────────────────────────────────

    async def _kazanma_kontrol(self) -> bool:
        vampir = self._vampir_sayısı()
        köylü  = self._köylü_sayısı()

        if vampir == 0:
            await self._oyun_bitti("köylü")
            return True
        if vampir >= köylü:
            await self._oyun_bitti("vampir")
            return True
        return False

    async def _oyun_bitti(self, kazanan: str):
        if kazanan == "köylü":
            başlık   = "🌟 Köylüler Kazandı!"
            renk     = discord.Color.green()
            açıklama = "Tüm vampirler temizlendi! Köy güvende! 🎉"
            tag      = "victory celebration villagers"
        else:
            başlık   = "🧛 Vampirler Kazandı!"
            renk     = discord.Color.dark_red()
            açıklama = "Vampirler köyü ele geçirdi! Geceler artık daha karanlık... 🌙"
            tag      = "vampire evil laugh win"

        gif = await giphy(tag)
        e   = discord.Embed(title=başlık, description=açıklama, color=renk)
        if gif:
            e.set_image(url=gif)

        satırlar = []
        for oyuncu in self.oyuncular:
            rol    = self.roller[oyuncu.id]
            durum  = "✅" if oyuncu in self.yaşayanlar else "💀"
            satırlar.append(f"{durum} {oyuncu.mention} — {ROL_EMOJI[rol]} {rol.capitalize()}")

        e.add_field(name="Tüm Roller", value="\n".join(satırlar), inline=False)
        e.timestamp = discord.utils.utcnow()

        tekrar = VampirTekrarView(self.oyuncular)
        msg = await self.kanal.send(embed=e, view=tekrar)
        tekrar.msg = msg

    # ── Oyunu Başlat ──────────────────────────────────────────────────────────

    async def başlat(self):
        roller_listesi = _rol_dagit(len(self.oyuncular))
        random.shuffle(roller_listesi)
        for oyuncu, rol in zip(self.oyuncular, roller_listesi):
            self.roller[oyuncu.id] = rol

        # Her oyuncuya DM ile rolünü gönder
        dm_hatası = []
        for oyuncu in self.oyuncular:
            rol = self.roller[oyuncu.id]
            vampir_bilgi = ""
            if rol == "vampir":
                diğer = [o for o in self.oyuncular if self.roller[o.id] == "vampir" and o.id != oyuncu.id]
                vampir_bilgi = (
                    f"\n\n🧛 **Vampir Takımın:** {', '.join(o.display_name for o in diğer)}"
                    if diğer else "\n\n🧛 **Sen tek vampirsin!**"
                )
            try:
                await oyuncu.send(
                    f"🎭 **Vampir Köylü — Rolün**\n\n"
                    f"{ROL_EMOJI[rol]} **{rol.capitalize()}**\n"
                    f"_{ROL_TANIM[rol]}_{vampir_bilgi}"
                )
            except discord.Forbidden:
                dm_hatası.append(oyuncu.display_name)

        sayım = Counter(roller_listesi)
        rol_satır = "\n".join(
            f"{ROL_EMOJI[r]} {r.capitalize()}: {sayım[r]}"
            for r in _ROL_SIRA if r in sayım
        )

        dm_uyarı = ""
        if dm_hatası:
            dm_uyarı = f"\n\n⚠️ DM gönderilemeyen oyuncular: {', '.join(dm_hatası)}"

        e = discord.Embed(
            title="🧛 Vampir Köylü Başlıyor!",
            description=(
                f"**{len(self.oyuncular)} oyuncu** ile oyun başlıyor!\n\n"
                "📬 **Herkes rolünü DM olarak aldı.** Gelen kutunuzu kontrol edin!\n"
                "Vampirler takım arkadaşlarını tanır. Özel roller gece eylem yapar."
                f"{dm_uyarı}"
            ),
            color=discord.Color.dark_red(),
        )
        e.add_field(name="Rol Dağılımı", value=rol_satır, inline=False)
        e.add_field(
            name=f"Oyuncular ({len(self.oyuncular)})",
            value="\n".join(f"• {o.mention}" for o in self.oyuncular),
            inline=False,
        )
        e.add_field(
            name="Nasıl Oynanır?",
            value=(
                "🌙 **Gece:** Vampirler kurban seçer, Doktor korur, Kahin rol öğrenir.\n"
                "☀️ **Gündüz:** Herkes tartışır ve oy kullanarak birini idam eder.\n"
                "🏆 **Köylüler:** Tüm vampirleri bulun!\n"
                "🧛 **Vampirler:** Köylülerle eşit veya daha fazla olun!"
            ),
            inline=False,
        )
        e.timestamp = discord.utils.utcnow()
        await self.kanal.send(embed=e)

        await asyncio.sleep(5)
        await self._gece_başlat()

    # ── Gece Fazı ─────────────────────────────────────────────────────────────

    async def _gece_başlat(self):
        self.gece_sayısı += 1
        self.vampir_oyları.clear()
        self.doktor_koruması = None
        self.kahin_görevi    = None
        self.gece_tamamlayanlar.clear()
        self._gece_cozuluyor = False

        e = discord.Embed(
            title=f"🌙 {self.gece_sayısı}. Gece Başladı!",
            description=(
                "Köy uykuya dalıyor...\n\n"
                "🧛 **Vampirler** • 👨‍⚕️ **Doktor** • 🔮 **Kahin** → Butona basarak gece eylemini seç.\n"
                "👨‍🌾 **Köylüler** → Sabahı bekle. 💤\n\n"
                "*(Rolünü hatırlamak için DM'ine bakabilirsin)*"
            ),
            color=discord.Color.from_rgb(15, 10, 50),
        )
        e.add_field(
            name=f"Hayatta Kalanlar ({len(self.yaşayanlar)})",
            value="\n".join(f"• {o.mention}" for o in self.yaşayanlar),
            inline=False,
        )
        e.set_footer(text=f"⏱️ {GECE_SURESI} saniye")
        e.timestamp = discord.utils.utcnow()

        view = GeceView(self)
        self.aktif_gece_view = view
        msg = await self.kanal.send(embed=e, view=view)
        view.msg = msg
        self.gece_mesaj = msg

    async def _gece_eylem_kontrol(self):
        if self._gece_cozuluyor:
            return
        beklenenler = self._beklenen_gece_aktörler()
        if beklenenler and beklenenler.issubset(self.gece_tamamlayanlar):
            self._gece_cozuluyor = True
            v = self.aktif_gece_view
            if v and not v._bitti:
                v._bitti = True
                v.stop()
                for c in v.children:
                    c.disabled = True
                if self.gece_mesaj:
                    try:
                        await self.gece_mesaj.edit(view=v)
                    except discord.HTTPException:
                        pass
            await self._gece_coz()

    async def _gece_coz(self):
        # Vampir kurban
        kurban_id: int | None = None
        if self.vampir_oyları:
            kurban_id = Counter(self.vampir_oyları.values()).most_common(1)[0][0]

        öldü: discord.Member | None = None
        kurtarıldı = False

        if kurban_id is not None:
            if kurban_id == self.doktor_koruması:
                kurtarıldı = True
            else:
                öldü = self._bul(kurban_id)
                if öldü and öldü in self.yaşayanlar:
                    self.yaşayanlar.remove(öldü)

        # Gece view kapat
        v = self.aktif_gece_view
        if v:
            for c in v.children:
                c.disabled = True
            if self.gece_mesaj:
                try:
                    await self.gece_mesaj.edit(view=v)
                except discord.HTTPException:
                    pass

        # Sabah özeti
        e = discord.Embed(title="🌅 Sabah Oldu!", color=discord.Color.from_rgb(255, 200, 50))

        if kurtarıldı:
            e.description = "🌙 Gece geçti...\n\n💉 **Doktor birini kurtardı! Bu gece kimse ölmedi!**"
        elif öldü:
            e.description = f"🌙 Gece geçti...\n\n💀 **{öldü.mention}** bu gece hayatını kaybetti!"
            e.add_field(
                name="Gerçek Rolü",
                value=f"{ROL_EMOJI.get(self.roller[öldü.id], '❓')} {self.roller[öldü.id].capitalize()}",
                inline=False,
            )
        else:
            e.description = "🌙 Gece geçti...\n\n😴 Bu gece kimse ölmedi."

        e.add_field(
            name=f"Hayatta Kalanlar ({len(self.yaşayanlar)})",
            value="\n".join(f"• {o.mention}" for o in self.yaşayanlar) or "—",
            inline=False,
        )
        e.timestamp = discord.utils.utcnow()
        await self.kanal.send(embed=e)

        if öldü and self.roller.get(öldü.id) == "avcı":
            await self._avci_tetik(öldü, "gunduz")
            return

        if await self._kazanma_kontrol():
            return

        await asyncio.sleep(4)
        await self._gunduz_başlat()

    # ── Gündüz Fazı ───────────────────────────────────────────────────────────

    async def _gunduz_başlat(self):
        self.gunduz_oyları.clear()
        self.gunduz_tamamlayanlar.clear()

        e = discord.Embed(
            title=f"☀️ Gündüz — {self.gece_sayısı}. Günün Oylaması",
            description=(
                "**Tartışın ve karar verin!**\n\n"
                f"Köyde **{len(self.yaşayanlar)}** kişi hayatta.\n"
                "Aralarında vampir var mı? Oylayın ve birini idam edin!"
            ),
            color=discord.Color.from_rgb(255, 220, 80),
        )
        e.add_field(
            name=f"Hayatta Kalanlar ({len(self.yaşayanlar)})",
            value="\n".join(f"• {o.mention}" for o in self.yaşayanlar),
            inline=False,
        )
        e.set_footer(text=f"⏱️ {GUNDUZ_SURESI} saniye — 0/{len(self.yaşayanlar)} oy kullandı")
        e.timestamp = discord.utils.utcnow()

        view = GunduzOyView(self)
        self.aktif_gunduz_view = view
        msg = await self.kanal.send(embed=e, view=view)
        view.msg = msg
        self.gunduz_mesaj = msg

    async def _gunduz_coz(self):
        v = self.aktif_gunduz_view
        if v:
            for c in v.children:
                c.disabled = True
            if self.gunduz_mesaj:
                try:
                    await self.gunduz_mesaj.edit(view=v)
                except discord.HTTPException:
                    pass

        elenecek: discord.Member | None = None
        beraberlik = False

        if self.gunduz_oyları:
            en_çok = Counter(self.gunduz_oyları.values()).most_common()
            if len(en_çok) > 1 and en_çok[0][1] == en_çok[1][1]:
                beraberlik = True
            else:
                elenecek = self._bul(en_çok[0][0])
                if elenecek and elenecek in self.yaşayanlar:
                    self.yaşayanlar.remove(elenecek)
                else:
                    elenecek = None

        if beraberlik:
            e = discord.Embed(
                title="⚖️ Oylar Eşit!",
                description="Bu gündüz kimse idam edilmedi. Vampirler şimdilik güvende!",
                color=discord.Color.greyple(),
            )
            e.timestamp = discord.utils.utcnow()
            await self.kanal.send(embed=e)

        elif not self.gunduz_oyları:
            e = discord.Embed(
                title="🤫 Kimse Oy Kullanmadı",
                description="Bu gündüz kimse idam edilmedi.",
                color=discord.Color.greyple(),
            )
            e.timestamp = discord.utils.utcnow()
            await self.kanal.send(embed=e)

        elif elenecek:
            oy_detay = []
            for voter_id, target_id in self.gunduz_oyları.items():
                voter  = self._bul(voter_id)
                target = self._bul(target_id)
                if voter and target:
                    oy_detay.append(f"• {voter.display_name} → {target.display_name}")

            e = discord.Embed(
                title="⚖️ Mahkeme Kararı!",
                description=f"**{elenecek.mention}** köy halkı tarafından ipe gönderildi!",
                color=discord.Color.dark_red(),
            )
            e.add_field(
                name="Gerçek Rolü",
                value=f"{ROL_EMOJI.get(self.roller[elenecek.id], '❓')} {self.roller[elenecek.id].capitalize()}",
                inline=False,
            )
            if oy_detay:
                e.add_field(name="Oy Dökümü", value="\n".join(oy_detay[:10]), inline=False)
            e.timestamp = discord.utils.utcnow()
            await self.kanal.send(embed=e)

            if self.roller[elenecek.id] == "avcı":
                await self._avci_tetik(elenecek, "gece")
                return

        if await self._kazanma_kontrol():
            return

        await asyncio.sleep(4)
        await self._gece_başlat()

    # ── Avcı Tetikleyici ──────────────────────────────────────────────────────

    async def _avci_tetik(self, avcı: discord.Member, sonraki_faz: str):
        if not self.yaşayanlar:
            if not await self._kazanma_kontrol():
                await asyncio.sleep(3)
                if sonraki_faz == "gunduz":
                    await self._gunduz_başlat()
                else:
                    await self._gece_başlat()
            return

        self._avci_event.clear()
        self._avci_hedef = None

        e = discord.Embed(
            title="🏹 Son Nefes!",
            description=(
                f"**{avcı.mention}** bir **Avcı** idi!\n\n"
                f"Son nefesinde birisini yanında götürebilir.\n"
                f"⏳ **{AVCI_SURESI} saniye** içinde seçimini yap!"
            ),
            color=discord.Color.orange(),
        )
        e.timestamp = discord.utils.utcnow()

        view = AvcıSonHamleView(self, avcı)
        msg  = await self.kanal.send(embed=e, view=view)
        view.msg = msg

        try:
            await asyncio.wait_for(self._avci_event.wait(), timeout=float(AVCI_SURESI + 3))
        except asyncio.TimeoutError:
            pass

        if self._avci_hedef:
            hedef = self._bul(self._avci_hedef)
            if hedef and hedef in self.yaşayanlar:
                self.yaşayanlar.remove(hedef)
                e2 = discord.Embed(
                    title="🏹 Avcının Son Oku!",
                    description=f"**{avcı.display_name}** son nefesinde **{hedef.mention}**'i yanında götürdü!",
                    color=discord.Color.dark_orange(),
                )
                e2.add_field(
                    name="Rolü",
                    value=f"{ROL_EMOJI.get(self.roller[hedef.id], '❓')} {self.roller[hedef.id].capitalize()}",
                    inline=False,
                )
                e2.timestamp = discord.utils.utcnow()
                await self.kanal.send(embed=e2)

        if await self._kazanma_kontrol():
            return

        await asyncio.sleep(3)
        if sonraki_faz == "gunduz":
            await self._gunduz_başlat()
        else:
            await self._gece_başlat()


# ── Cog ───────────────────────────────────────────────────────────────────────

class VampirKoylu(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="vampirkoylu",
        description="Arkadaşlarla Vampir Köylü oyna! (4-12 oyuncu)"
    )
    async def vampirkoylu(self, interaction: discord.Interaction):
        view = VampirKoyluLobiView(interaction.user)  # type: ignore[arg-type]
        await interaction.response.send_message(embed=view._embed(), view=view)
        view.msg = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(VampirKoylu(bot))
