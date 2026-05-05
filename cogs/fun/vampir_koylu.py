import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from collections import Counter
from ._shared import giphy
from .._v2 import (
    c_text, c_thumbnail, c_section, c_container, c_separator, c_media,
    respond, update, channel_send, msg_edit,
)

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
        self.kart: dict | None = None

    async def on_timeout(self):
        if not self._bitti:
            self._bitti = True
            self.stop()
            for c in self.children:
                c.disabled = True
            if self.msg and self.kart:
                try:
                    await msg_edit(self.msg, self.kart, view=self)
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

    def _card(self) -> dict:
        oyun     = self.oyun
        oy_sayısı = len(oyun.gunduz_oyları)
        toplam   = len(oyun.yaşayanlar)
        lines = [
            f"**☀️ Gündüz — {oyun.gece_sayısı}. Günün Oylaması**",
            "",
            "**Tartışın ve karar verin!**",
            "",
            f"Köyde **{toplam}** kişi hayatta.",
            "Aralarında vampir var mı? Oylayın ve birini idam edin!",
            "",
            "**Hayatta Kalanlar:**",
        ] + [f"• {o.mention}" for o in oyun.yaşayanlar] + [
            "",
            f"-# ⏱️ {GUNDUZ_SURESI} saniye — {oy_sayısı}/{toplam} oy kullandı",
        ]
        return c_container(c_text("\n".join(lines)), color=0xFFDC50)

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

        if self.msg:
            try:
                await msg_edit(self.msg, self._card(), view=self)
            except discord.HTTPException:
                pass

        if len(oyun.gunduz_oyları) >= len(oyun.yaşayanlar) and not self._bitti:
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
                    await msg_edit(self.msg, self._card(), view=self)
                except discord.HTTPException:
                    pass
            await self.oyun._gunduz_coz()


# ── Avcı Son Hamle View ───────────────────────────────────────────────────────

class AvcıSonHamleView(discord.ui.View):
    def __init__(self, oyun: "VampirKoyluOyunu", avcı: discord.Member, kart: dict):
        super().__init__(timeout=AVCI_SURESI)
        self.oyun   = oyun
        self.avcı   = avcı
        self.kart   = kart
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
        await update(interaction, self.kart, view=self)

    async def on_timeout(self):
        if not self._bitti:
            self._bitti = True
            self.oyun._avci_event.set()
            for c in self.children:
                c.disabled = True
            if self.msg:
                try:
                    await msg_edit(self.msg, self.kart, view=self)
                except discord.HTTPException:
                    pass


# ── Tekrar Oyna View ──────────────────────────────────────────────────────────

class VampirTekrarView(discord.ui.View):
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
    async def tekrar_btn(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyuncular:
            return await interaction.response.send_message("Bu oyuna dahil değildin!", ephemeral=True)
        btn.disabled = True
        self.stop()
        await update(interaction, *self.son_kart, view=self)
        lobi = VampirKoyluLobiView(interaction.user)
        new_msg = await channel_send(interaction.channel, *lobi._card(), view=lobi)
        lobi.msg = new_msg


# ── Lobi View ─────────────────────────────────────────────────────────────────

class VampirKoyluLobiView(discord.ui.View):
    def __init__(self, kurucu: discord.Member):
        super().__init__(timeout=LOBI_SURESI)
        self.kurucu    = kurucu
        self.oyuncular: list[discord.Member] = [kurucu]
        self.msg: discord.Message | None = None
        self._başladı  = False

    def _card(self, zaman_doldu: bool = False) -> tuple[dict, ...]:
        dagılım  = _rol_dagit(len(self.oyuncular))
        sayım    = Counter(dagılım)
        rol_satır = "\n".join(
            f"{ROL_EMOJI[r]} {r.capitalize()}: {sayım[r]}"
            for r in _ROL_SIRA if r in sayım
        )
        lines = (
            ["**🧛 Vampir Köylü — Lobi**", "",
             f"**{self.kurucu.mention}** bir oyun kurdu!",
             f"**Katılımcılar ({len(self.oyuncular)}/{MAX_OYUNCU}):**"]
            + [f"• {o.mention}" for o in self.oyuncular]
            + ["",
               f"**Bu sayıyla rol dağılımı:**\n{rol_satır}",
               "",
               f"-# Min {MIN_OYUNCU} • Max {MAX_OYUNCU} oyuncu • Kurucu başlatır"]
        )
        if zaman_doldu:
            lines.append("\n⏰ Lobi süresi doldu.")
        return (c_container(c_text("\n".join(lines)), color=0x8B0000),)

    async def on_timeout(self):
        if not self._başladı:
            for c in self.children:
                c.disabled = True
            if self.msg:
                try:
                    await msg_edit(self.msg, *self._card(zaman_doldu=True), view=self)
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
        await msg_edit(self.msg, *self._card(), view=self)
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
        await update(interaction,
            c_container(c_text(f"**🚫 Lobi İptal Edildi**\n\n{interaction.user.mention} lobi iptal etti."), color=0x95A5A6),
            view=self,
        )


# ── Oyun Motoru ───────────────────────────────────────────────────────────────

class VampirKoyluOyunu:
    def __init__(self, oyuncular, kanal, kurucu):
        self.oyuncular  = oyuncular[:]
        self.yaşayanlar = oyuncular[:]
        self.kanal      = kanal
        self.kurucu     = kurucu
        self.roller: dict[int, str] = {}
        self.gece_sayısı = 0

        self.vampir_oyları: dict[int, int] = {}
        self.doktor_koruması: int | None   = None
        self.kahin_görevi: int | None      = None
        self.gece_tamamlayanlar: set[int]  = set()
        self._gece_cozuluyor = False

        self.gunduz_oyları: dict[int, int]  = {}
        self.gunduz_tamamlayanlar: set[int] = set()

        self._avci_event = asyncio.Event()
        self._avci_hedef: int | None = None

        self.aktif_gece_view: GeceView | None       = None
        self.aktif_gunduz_view: GunduzOyView | None = None
        self.gece_mesaj: discord.Message | None     = None
        self.gunduz_mesaj: discord.Message | None   = None

    def _bul(self, uid: int) -> discord.Member | None:
        return next((o for o in self.oyuncular if o.id == uid), None)

    def _beklenen_gece_aktörler(self) -> set[int]:
        return {o.id for o in self.yaşayanlar if self.roller[o.id] in ("vampir", "doktor", "kahin")}

    def _vampir_sayısı(self) -> int:
        return sum(1 for o in self.yaşayanlar if self.roller[o.id] == "vampir")

    def _köylü_sayısı(self) -> int:
        return sum(1 for o in self.yaşayanlar if self.roller[o.id] != "vampir")

    async def _kazanma_kontrol(self) -> bool:
        if self._vampir_sayısı() == 0:
            await self._oyun_bitti("köylü")
            return True
        if self._vampir_sayısı() >= self._köylü_sayısı():
            await self._oyun_bitti("vampir")
            return True
        return False

    async def _oyun_bitti(self, kazanan: str):
        if kazanan == "köylü":
            başlık = "🌟 Köylüler Kazandı!"
            renk   = 0x57F287
            açıklama = "Tüm vampirler temizlendi! Köy güvende! 🎉"
            tag    = "victory celebration villagers"
        else:
            başlık = "🧛 Vampirler Kazandı!"
            renk   = 0x8B0000
            açıklama = "Vampirler köyü ele geçirdi! Geceler artık daha karanlık... 🌙"
            tag    = "vampire evil laugh win"

        gif = await giphy(tag)

        satırlar = []
        for oyuncu in self.oyuncular:
            rol   = self.roller[oyuncu.id]
            durum = "✅" if oyuncu in self.yaşayanlar else "💀"
            satırlar.append(f"{durum} {oyuncu.mention} — {ROL_EMOJI[rol]} {rol.capitalize()}")

        items: list[dict] = [
            c_text(f"**{başlık}**\n\n{açıklama}\n\n**Tüm Roller:**\n" + "\n".join(satırlar))
        ]
        if gif:
            items.append(c_separator())
            items.append(c_media(gif))
        son_kart = (c_container(*items, color=renk),)

        tekrar = VampirTekrarView(self.oyuncular, son_kart)
        msg = await channel_send(self.kanal, *son_kart, view=tekrar)
        tekrar.msg = msg

    async def başlat(self):
        roller_listesi = _rol_dagit(len(self.oyuncular))
        random.shuffle(roller_listesi)
        for oyuncu, rol in zip(self.oyuncular, roller_listesi):
            self.roller[oyuncu.id] = rol

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
        dm_uyarı = f"\n\n⚠️ DM gönderilemeyen oyuncular: {', '.join(dm_hatası)}" if dm_hatası else ""

        baslangic_text = (
            f"**🧛 Vampir Köylü Başlıyor!**\n\n"
            f"**{len(self.oyuncular)} oyuncu** ile oyun başlıyor!\n\n"
            "📬 **Herkes rolünü DM olarak aldı.** Gelen kutunuzu kontrol edin!\n"
            "Vampirler takım arkadaşlarını tanır. Özel roller gece eylem yapar."
            f"{dm_uyarı}\n\n"
            f"**Rol Dağılımı:**\n{rol_satır}\n\n"
            f"**Oyuncular ({len(self.oyuncular)}):**\n"
            + "\n".join(f"• {o.mention}" for o in self.oyuncular)
            + "\n\n"
            "🌙 **Gece:** Vampirler kurban seçer, Doktor korur, Kahin rol öğrenir.\n"
            "☀️ **Gündüz:** Herkes tartışır ve oy kullanarak birini idam eder.\n"
            "🏆 **Köylüler:** Tüm vampirleri bulun!\n"
            "🧛 **Vampirler:** Köylülerle eşit veya daha fazla olun!"
        )
        await channel_send(self.kanal, c_container(c_text(baslangic_text), color=0x8B0000))
        await asyncio.sleep(5)
        await self._gece_başlat()

    async def _gece_başlat(self):
        self.gece_sayısı += 1
        self.vampir_oyları.clear()
        self.doktor_koruması = None
        self.kahin_görevi    = None
        self.gece_tamamlayanlar.clear()
        self._gece_cozuluyor = False

        yaşayanlar_str = "\n".join(f"• {o.mention}" for o in self.yaşayanlar)
        gece_text = (
            f"**🌙 {self.gece_sayısı}. Gece Başladı!**\n\n"
            "Köy uykuya dalıyor...\n\n"
            "🧛 **Vampirler** • 👨‍⚕️ **Doktor** • 🔮 **Kahin** → Butona basarak gece eylemini seç.\n"
            "👨‍🌾 **Köylüler** → Sabahı bekle. 💤\n\n"
            "*(Rolünü hatırlamak için DM'ine bakabilirsin)*\n\n"
            f"**Hayatta Kalanlar ({len(self.yaşayanlar)}):**\n{yaşayanlar_str}\n\n"
            f"-# ⏱️ {GECE_SURESI} saniye"
        )
        gece_kart = c_container(c_text(gece_text), color=0x0A0A32)

        view = GeceView(self)
        view.kart = gece_kart
        self.aktif_gece_view = view
        msg = await channel_send(self.kanal, gece_kart, view=view)
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
                if self.gece_mesaj and v.kart:
                    try:
                        await msg_edit(self.gece_mesaj, v.kart, view=v)
                    except discord.HTTPException:
                        pass
            await self._gece_coz()

    async def _gece_coz(self):
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

        v = self.aktif_gece_view
        if v:
            for c in v.children:
                c.disabled = True
            if self.gece_mesaj and v.kart:
                try:
                    await msg_edit(self.gece_mesaj, v.kart, view=v)
                except discord.HTTPException:
                    pass

        yaşayanlar_str = "\n".join(f"• {o.mention}" for o in self.yaşayanlar) or "—"
        if kurtarıldı:
            sabah_text = (
                "**🌅 Sabah Oldu!**\n\n"
                "🌙 Gece geçti...\n\n"
                "💉 **Doktor birini kurtardı! Bu gece kimse ölmedi!**\n\n"
                f"**Hayatta Kalanlar ({len(self.yaşayanlar)}):**\n{yaşayanlar_str}"
            )
        elif öldü:
            rol_str = f"{ROL_EMOJI.get(self.roller[öldü.id], '❓')} {self.roller[öldü.id].capitalize()}"
            sabah_text = (
                "**🌅 Sabah Oldu!**\n\n"
                f"🌙 Gece geçti...\n\n"
                f"💀 **{öldü.mention}** bu gece hayatını kaybetti!\n"
                f"Gerçek rolü: {rol_str}\n\n"
                f"**Hayatta Kalanlar ({len(self.yaşayanlar)}):**\n{yaşayanlar_str}"
            )
        else:
            sabah_text = (
                "**🌅 Sabah Oldu!**\n\n"
                "🌙 Gece geçti...\n\n"
                "😴 Bu gece kimse ölmedi.\n\n"
                f"**Hayatta Kalanlar ({len(self.yaşayanlar)}):**\n{yaşayanlar_str}"
            )

        await channel_send(self.kanal, c_container(c_text(sabah_text), color=0xFFC832))

        if öldü and self.roller.get(öldü.id) == "avcı":
            await self._avci_tetik(öldü, "gunduz")
            return

        if await self._kazanma_kontrol():
            return

        await asyncio.sleep(4)
        await self._gunduz_başlat()

    async def _gunduz_başlat(self):
        self.gunduz_oyları.clear()
        self.gunduz_tamamlayanlar.clear()

        view = GunduzOyView(self)
        self.aktif_gunduz_view = view
        msg = await channel_send(self.kanal, view._card(), view=view)
        view.msg = msg
        self.gunduz_mesaj = msg

    async def _gunduz_coz(self):
        v = self.aktif_gunduz_view
        if v:
            for c in v.children:
                c.disabled = True
            if self.gunduz_mesaj:
                try:
                    await msg_edit(self.gunduz_mesaj, v._card(), view=v)
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
            await channel_send(self.kanal, c_container(
                c_text("**⚖️ Oylar Eşit!**\n\nBu gündüz kimse idam edilmedi. Vampirler şimdilik güvende!"),
                color=0x95A5A6,
            ))
        elif not self.gunduz_oyları:
            await channel_send(self.kanal, c_container(
                c_text("**🤫 Kimse Oy Kullanmadı**\n\nBu gündüz kimse idam edilmedi."),
                color=0x95A5A6,
            ))
        elif elenecek:
            oy_detay = []
            for voter_id, target_id in self.gunduz_oyları.items():
                voter  = self._bul(voter_id)
                target = self._bul(target_id)
                if voter and target:
                    oy_detay.append(f"• {voter.display_name} → {target.display_name}")

            rol_str = f"{ROL_EMOJI.get(self.roller[elenecek.id], '❓')} {self.roller[elenecek.id].capitalize()}"
            oy_text = "\n".join(oy_detay[:10]) if oy_detay else ""
            mahkeme_text = (
                f"**⚖️ Mahkeme Kararı!**\n\n"
                f"**{elenecek.mention}** köy halkı tarafından ipe gönderildi!\n"
                f"Gerçek rolü: {rol_str}"
                + (f"\n\n**Oy Dökümü:**\n{oy_text}" if oy_text else "")
            )
            await channel_send(self.kanal, c_container(c_text(mahkeme_text), color=0x8B0000))

            if self.roller[elenecek.id] == "avcı":
                await self._avci_tetik(elenecek, "gece")
                return

        if await self._kazanma_kontrol():
            return

        await asyncio.sleep(4)
        await self._gece_başlat()

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

        avci_text = (
            f"**🏹 Son Nefes!**\n\n"
            f"**{avcı.mention}** bir **Avcı** idi!\n\n"
            f"Son nefesinde birisini yanında götürebilir.\n"
            f"⏳ **{AVCI_SURESI} saniye** içinde seçimini yap!"
        )
        avci_kart = c_container(c_text(avci_text), color=0xF0A030)

        view = AvcıSonHamleView(self, avcı, avci_kart)
        msg  = await channel_send(self.kanal, avci_kart, view=view)
        view.msg = msg

        try:
            await asyncio.wait_for(self._avci_event.wait(), timeout=float(AVCI_SURESI + 3))
        except asyncio.TimeoutError:
            pass

        if self._avci_hedef:
            hedef = self._bul(self._avci_hedef)
            if hedef and hedef in self.yaşayanlar:
                self.yaşayanlar.remove(hedef)
                rol_str = f"{ROL_EMOJI.get(self.roller[hedef.id], '❓')} {self.roller[hedef.id].capitalize()}"
                await channel_send(self.kanal, c_container(
                    c_text(
                        f"**🏹 Avcının Son Oku!**\n\n"
                        f"**{avcı.display_name}** son nefesinde **{hedef.mention}**'i yanında götürdü!\n"
                        f"Rolü: {rol_str}"
                    ),
                    color=0xE67E22,
                ))

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

    @app_commands.command(name="vampirkoylu", description="Arkadaşlarla Vampir Köylü oyna! (4-12 oyuncu)")
    async def vampirkoylu(self, interaction: discord.Interaction):
        view = VampirKoyluLobiView(interaction.user)  # type: ignore[arg-type]
        view.msg = await respond(interaction, *view._card(), view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(VampirKoylu(bot))
