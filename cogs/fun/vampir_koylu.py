import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from collections import Counter
from ._shared import giphy
from .._v2 import (
    COLORS, c_card, c_action_card, c_text, c_thumbnail, c_section, c_container, c_separator, c_media,
    c_progress, respond, update, channel_send, msg_edit, followup as v2_followup,
)

LOBI_SURESI   = 120
GECE_SURESI   = 90
GUNDUZ_SURESI = 120
AVCI_SURESI   = 30
MIN_OYUNCU    = 4
MAX_OYUNCU    = 12

# Renkler (faza özel)
_C_NIGHT  = 0x0A0A32   # gece
_C_DAY    = 0xFFDC50   # gündüz
_C_DAWN   = 0xFFC832   # şafak
_C_BLOOD  = 0x8B0000   # vampir
_C_HUNTER = 0xF0A030

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


async def _v2_err(interaction: discord.Interaction, title: str, body: str = "", color: int = COLORS.DANGER):
    thumb = str(interaction.client.user.display_avatar.url)
    if interaction.response.is_done():
        await v2_followup(interaction, c_card(f"## {title}", body=body, thumbnail=thumb, color=color), ephemeral=True)
    else:
        await respond(interaction, c_card(f"## {title}", body=body, thumbnail=thumb, color=color), ephemeral=True)


# ── Gece Aksiyon View (Ephemeral) ─────────────────────────────────────────────

class GeceAksiyonView(discord.ui.View):
    def __init__(self, oyun: "VampirKoyluOyunu", oyuncu: discord.Member, rol: str):
        super().__init__(timeout=GECE_SURESI)
        self.oyun       = oyun
        self.oyuncu     = oyuncu
        self.rol        = rol
        self.tamamlandı = False
        self._takım_bilgi_kart: dict | None = None
        self._build_select()

    def _build_select(self):
        oyun = self.oyun
        rol  = self.rol

        if rol == "vampir":
            diğer = [o for o in oyun.yaşayanlar if oyun.roller[o.id] == "vampir" and o.id != self.oyuncu.id]
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

    def _result_card(self, title: str, body: str, color: int = _C_NIGHT) -> dict:
        thumb = str(self.oyuncu.display_avatar.url)
        return c_container(
            c_section(c_text(f"## {title}"), accessory=c_thumbnail(thumb)),
            c_separator(),
            c_text(body),
            color=color,
        )

    async def _vampir_cb(self, interaction: discord.Interaction):
        if self.tamamlandı:
            return await interaction.response.defer()
        self.tamamlandı = True
        hedef_id = int(self.children[0].values[0])
        self.oyun.vampir_oyları[self.oyuncu.id] = hedef_id
        self.oyun.gece_tamamlayanlar.add(self.oyuncu.id)
        self._disable_all()
        hedef = self._bul(hedef_id)

        # Vampir kanalına bilgi
        if self.oyun.vampir_kanal and hedef:
            try:
                await channel_send(self.oyun.vampir_kanal, c_container(
                    c_text(
                        f"🧛 **{self.oyuncu.display_name}** kurbanını seçti: 💀 **{hedef.display_name}**"
                    ),
                    color=_C_BLOOD,
                ))
            except Exception:
                pass

        await update(interaction, self._result_card(
            "🧛 Kurban Seçildi",
            f"💀 **{hedef.display_name if hedef else '?'}** seçildi.\n\n"
            f"Eğer Doktor başkasını korursa hedefin ölecek. Sabahı bekle...",
            color=_C_BLOOD,
        ), view=self)
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
        await update(interaction, self._result_card(
            "👨‍⚕️ Koruma Yerleştirildi",
            f"💉 **{hedef.display_name if hedef else '?'}** bu gece korunuyor.\n\n"
            f"Vampirler onu seçerse hayatta kalacak. Sabahı bekle...",
            color=COLORS.INFO,
        ), view=self)
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
        rol_emoji = ROL_EMOJI.get(hedef_rol, "❓")
        is_vampire = hedef_rol == "vampir"
        await update(interaction, self._result_card(
            "🔮 Vizyon",
            f"### {hedef.display_name if hedef else '?'}\n\n"
            f"{rol_emoji} **{hedef_rol.capitalize()}**\n\n"
            f"{'⚠️ Bu kişi VAMPİR! Köylüleri uyar ama dikkatli ol — vampirler seni hedef alabilir.' if is_vampire else '✅ Bu kişi vampir değil. Onunla işbirliği yapabilirsin.'}",
            color=0x9B59B6,
        ), view=self)
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
        thumb = str(interaction.client.user.display_avatar.url)

        if interaction.user not in oyun.yaşayanlar:
            return await _v2_err(interaction, "💀 Hayatta Değilsin", "Bu oyunda elendin veya zaten katılmadın.")
        if uid in oyun.gece_tamamlayanlar:
            return await _v2_err(interaction, "🔁 Tamamlandı", "Gece eylemini zaten yaptın.", COLORS.WARNING)

        rol = oyun.roller.get(uid)
        if rol not in ("vampir", "doktor", "kahin"):
            return await respond(interaction, c_card(
                "## 🌙 Köylü Uyumakta",
                body="Sen **köylüsün**, bu gece yapacak bir eylemin yok. Uy ve sabahı bekle. 💤",
                thumbnail=thumb,
                color=_C_NIGHT,
            ), ephemeral=True)

        view = GeceAksiyonView(oyun, interaction.user, rol)

        # Rol özet kartı
        items: list[dict] = [
            c_section(
                c_text(f"## {ROL_EMOJI[rol]} {rol.capitalize()}\n-# Gece eylemi"),
                accessory=c_thumbnail(str(interaction.user.display_avatar.url)),
            ),
            c_separator(),
            c_text(f"_{ROL_TANIM[rol]}_"),
        ]

        # Vampirler için takım durumu
        if rol == "vampir":
            diğer = [o for o in oyun.yaşayanlar if oyun.roller[o.id] == "vampir" and o.id != interaction.user.id]
            if diğer:
                takım_satırları = []
                for d in diğer:
                    if d.id in oyun.vampir_oyları:
                        hedef = next((o for o in oyun.oyuncular if o.id == oyun.vampir_oyları[d.id]), None)
                        takım_satırları.append(f"🧛 {d.display_name} → 💀 **{hedef.display_name if hedef else '?'}**")
                    else:
                        takım_satırları.append(f"🧛 {d.display_name} → ⏳ _henüz seçmedi_")
                items.append(c_separator())
                items.append(c_text(f"**🩸 Vampir Takımın**\n" + "\n".join(takım_satırları)))
                if oyun.vampir_kanal:
                    items.append(c_separator())
                    items.append(c_text(f"-# 💬 Özel sohbet: {oyun.vampir_kanal.mention}"))
            else:
                items.append(c_separator())
                items.append(c_text("**🩸 Sen tek vampirsin!**\nKararını tek başına vermen gerekecek."))

        items.append(c_separator())
        items.append(c_text("👇 Aşağıdan hedefini seç:"))

        await respond(interaction, c_container(*items, color=_C_NIGHT), view=view, ephemeral=True)


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
        progress = c_progress(oy_sayısı, max(toplam, 1), length=14)

        yaşayan_satırları = " · ".join(o.mention for o in oyun.yaşayanlar)

        return c_container(
            c_text(f"## ☀️ Gündüz Oylaması\n-# Gün **{oyun.gece_sayısı}** · Tartışın ve karar verin!"),
            c_separator(),
            c_text(
                f"**👥 Köyde {toplam} kişi hayatta**\n"
                f"{yaşayan_satırları}"
            ),
            c_separator(),
            c_text(
                f"**🗳️ Oylama**\n"
                f"`{progress}` `{oy_sayısı}/{toplam}` oy verildi"
            ),
            c_separator(),
            c_text(f"-# 👆 Seçim menüsünden idam edilecek kişiyi seç · ⏱️ {GUNDUZ_SURESI}sn"),
            color=_C_DAY,
        )

    async def _oy_cb(self, interaction: discord.Interaction):
        uid  = interaction.user.id
        oyun = self.oyun
        thumb = str(interaction.client.user.display_avatar.url)

        if interaction.user not in oyun.yaşayanlar:
            return await _v2_err(interaction, "💀 Hayatta Değilsin", "Elendin, oy kullanamazsın.")
        if uid in oyun.gunduz_tamamlayanlar:
            return await _v2_err(interaction, "🔁 Zaten Oyladın", "Bu gün zaten oy kullandın.", COLORS.WARNING)

        hedef_id = int(self.children[0].values[0])
        if hedef_id == uid:
            return await _v2_err(interaction, "🚫 Geçersiz", "Kendine oy veremezsin!", COLORS.WARNING)

        oyun.gunduz_oyları[uid] = hedef_id
        oyun.gunduz_tamamlayanlar.add(uid)

        hedef = next((o for o in oyun.yaşayanlar if o.id == hedef_id), None)
        await respond(interaction, c_card(
            "## ✅ Oyun Kaydedildi",
            body=f"🎯 Oy verdiğin kişi: **{hedef.display_name if hedef else '?'}**",
            thumbnail=thumb,
            color=COLORS.SUCCESS,
        ), ephemeral=True)

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
            return await _v2_err(interaction, "⛔ Erişim", "Bu sadece **Avcı**'nın menüsü.")
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
            return await _v2_err(interaction, "⛔ Erişim", "Bu oyuna dahil değildin.")
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

    def _card(self, *, kapanis: str | None = None, color: int = _C_BLOOD) -> tuple[dict, ...]:
        dağılım = _rol_dagit(len(self.oyuncular))
        sayım = Counter(dağılım)
        rol_satır = " · ".join(
            f"{ROL_EMOJI[r]} **{sayım[r]}**"
            for r in _ROL_SIRA if r in sayım
        )

        oyuncu_listesi = "\n".join(f"🪑 {o.mention}" for o in self.oyuncular)

        items: list[dict] = [
            c_text("## 🧛 Vampir Köylü — Lobi"),
            c_separator(),
            c_text(
                f"**👥 Oyuncular** · `{len(self.oyuncular)}/{MAX_OYUNCU}`\n"
                f"{oyuncu_listesi}"
            ),
            c_separator(),
            c_text(
                f"**🎭 Bu sayıyla rol dağılımı**\n"
                f"{rol_satır}"
            ),
            c_separator(),
            c_text(
                f"**📐 Kurallar**\n"
                f"┗ Min `{MIN_OYUNCU}` · Max `{MAX_OYUNCU}` oyuncu\n"
                f"┗ Gece `{GECE_SURESI}` sn · Gündüz `{GUNDUZ_SURESI}` sn\n"
                f"┗ 2+ vampir varsa **özel vampir sohbet kanalı** açılır 🩸"
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
        if len(self.oyuncular) < MIN_OYUNCU:
            return await _v2_err(interaction, "⚠️ Yetersiz Oyuncu", f"En az **{MIN_OYUNCU}** oyuncu gerekli.\nŞu an: `{len(self.oyuncular)}`", COLORS.WARNING)
        self._başladı = True
        self.stop()
        for c in self.children:
            c.disabled = True
        await interaction.response.defer()
        assert self.msg
        await msg_edit(self.msg, *self._card(kapanis="▶️ **Oyun başlıyor...** 🌙", color=COLORS.SUCCESS), view=self)
        oyun = VampirKoyluOyunu(list(self.oyuncular), interaction.channel, self.kurucu)  # type: ignore[arg-type]
        await oyun.başlat()

    @discord.ui.button(label="İptal", emoji="✖️", style=discord.ButtonStyle.danger)
    async def iptal_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.kurucu.id:
            return await _v2_err(interaction, "🚫 Yetki Yok", "Sadece **kurucu** iptal edebilir.")
        self._başladı = True
        self.stop()
        for c in self.children:
            c.disabled = True
        await update(interaction,
            c_card("## 🚫 Lobi İptal Edildi", body=f"{interaction.user.mention} lobiyi iptal etti.", color=0x95A5A6),
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

        # Vampirler arası özel kanal (2+ vampir varsa açılır)
        self.vampir_kanal: discord.TextChannel | None = None

    def _bul(self, uid: int) -> discord.Member | None:
        return next((o for o in self.oyuncular if o.id == uid), None)

    def _beklenen_gece_aktörler(self) -> set[int]:
        return {o.id for o in self.yaşayanlar if self.roller[o.id] in ("vampir", "doktor", "kahin")}

    def _vampir_sayısı(self) -> int:
        return sum(1 for o in self.yaşayanlar if self.roller[o.id] == "vampir")

    def _köylü_sayısı(self) -> int:
        return sum(1 for o in self.yaşayanlar if self.roller[o.id] != "vampir")

    def _vampirler(self) -> list[discord.Member]:
        return [o for o in self.oyuncular if self.roller.get(o.id) == "vampir"]

    async def _vampir_kanali_olustur(self) -> bool:
        """2+ vampir varsa onlara özel sohbet kanalı açar. Başarılıysa True döner."""
        guild = self.kanal.guild if hasattr(self.kanal, "guild") else None
        if not guild:
            return False

        vampirler = self._vampirler()
        if len(vampirler) < 2:
            return False

        # Bot'un kanal yönetme yetkisi var mı?
        me = guild.me
        if not me.guild_permissions.manage_channels:
            return False

        overwrites: dict = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                manage_channels=True, manage_messages=True, read_message_history=True,
            ),
        }
        for v in vampirler:
            overwrites[v] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
            )

        # Kategori (game kanalın kategorisi varsa onun altına aç)
        category = self.kanal.category if hasattr(self.kanal, "category") else None

        try:
            kanal_adi = f"vampir-meclisi-{random.randint(100, 999)}"
            self.vampir_kanal = await guild.create_text_channel(
                name=kanal_adi,
                overwrites=overwrites,
                category=category,
                topic=f"🧛 Vampir Köylü oyunu — {len(vampirler)} vampir için özel sohbet",
                reason="Vampir Köylü oyunu özel vampir sohbeti",
            )
        except (discord.Forbidden, discord.HTTPException):
            self.vampir_kanal = None
            return False

        # Açılış mesajı
        try:
            vampir_listesi = "\n".join(f"🧛 {v.mention}" for v in vampirler)
            await channel_send(self.vampir_kanal, c_container(
                c_section(
                    c_text("## 🩸 Vampir Meclisi"),
                    accessory=c_thumbnail(str(guild.icon.url) if guild.icon else str(vampirler[0].display_avatar.url)),
                ),
                c_separator(),
                c_text(
                    f"**Hoş geldiniz vampirler!**\n\n"
                    f"Burası size özel **gizli sohbet kanalı**. Köylüler buradaki konuşmaları göremez.\n\n"
                    f"**🩸 Takım**\n{vampir_listesi}\n\n"
                    f"💡 Strateji yapın, hedeflerinizi koordine edin, kahini bulmaya çalışın!"
                ),
                c_separator(),
                c_text(f"-# 🎭 Oyun: <#{self.kanal.id}> · 🧹 Bu kanal oyun bitince silinecek."),
                color=_C_BLOOD,
            ))
        except Exception:
            pass

        return True

    async def _vampir_kanali_sil(self):
        """Oyun bittiğinde vampir kanalını siler."""
        if self.vampir_kanal:
            try:
                # Önce kapanış mesajı
                await channel_send(self.vampir_kanal, c_card(
                    "## 🪦 Oyun Bitti",
                    body="Bu kanal **15 saniye içinde** silinecek...",
                    color=0x95A5A6,
                ))
                await asyncio.sleep(15)
                await self.vampir_kanal.delete(reason="Vampir Köylü oyunu sona erdi")
            except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                pass
            self.vampir_kanal = None

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
            renk   = COLORS.SUCCESS
            açıklama = "Tüm vampirler temizlendi! Köy güvende. 🎉"
            tag    = "victory celebration villagers"
        else:
            başlık = "🧛 Vampirler Kazandı!"
            renk   = _C_BLOOD
            açıklama = "Vampirler köyü ele geçirdi. Geceler artık daha karanlık... 🌙"
            tag    = "vampire evil laugh win"

        gif = await giphy(tag)

        rol_satırları: list[str] = []
        for oyuncu in self.oyuncular:
            rol   = self.roller[oyuncu.id]
            durum = "✅" if oyuncu in self.yaşayanlar else "💀"
            rol_satırları.append(f"{durum} {oyuncu.mention}\n┗ {ROL_EMOJI[rol]} **{rol.capitalize()}**")

        items: list[dict] = [
            c_text(f"## {başlık}\n-# {açıklama}"),
            c_separator(),
            c_text("**🎭 Tüm Roller**\n\n" + "\n\n".join(rol_satırları)),
        ]
        if gif:
            items.append(c_separator())
            items.append(c_media(gif))

        son_kart = (c_container(*items, color=renk),)
        tekrar = VampirTekrarView(self.oyuncular, son_kart)
        msg = await channel_send(self.kanal, *son_kart, view=tekrar)
        tekrar.msg = msg

        # Vampir kanalını sil
        await self._vampir_kanali_sil()

    async def başlat(self):
        roller_listesi = _rol_dagit(len(self.oyuncular))
        random.shuffle(roller_listesi)
        for oyuncu, rol in zip(self.oyuncular, roller_listesi):
            self.roller[oyuncu.id] = rol

        # 2+ vampir varsa özel kanal aç
        kanal_acildi = await self._vampir_kanali_olustur()

        # DM ile rolleri gönder
        dm_hatası: list[str] = []
        for oyuncu in self.oyuncular:
            rol = self.roller[oyuncu.id]
            extra_items: list[dict] = []
            if rol == "vampir":
                diğer = [o for o in self.oyuncular if self.roller[o.id] == "vampir" and o.id != oyuncu.id]
                if diğer:
                    takım_str = "\n".join(f"🧛 {o.display_name}" for o in diğer)
                    extra_items.append(c_separator())
                    extra_items.append(c_text(f"**🩸 Vampir Takımın**\n{takım_str}"))
                    if self.vampir_kanal:
                        extra_items.append(c_separator())
                        extra_items.append(c_text(f"**💬 Özel Sohbet**\n{self.vampir_kanal.mention} kanalında takımınla strateji konuşabilirsin!"))
                else:
                    extra_items.append(c_separator())
                    extra_items.append(c_text("**🩸 Sen tek vampirsin!**"))

            try:
                dm = await oyuncu.create_dm()
                await channel_send(dm, c_container(
                    c_section(
                        c_text(f"## 🎭 Rolün — {ROL_EMOJI[rol]} {rol.capitalize()}"),
                        accessory=c_thumbnail(str(oyuncu.display_avatar.url)),
                    ),
                    c_separator(),
                    c_text(f"_{ROL_TANIM[rol]}_"),
                    *extra_items,
                    c_separator(),
                    c_text(f"-# 🎮 Oyun: **Vampir Köylü** · 🧑‍🤝‍🧑 {len(self.oyuncular)} oyuncu"),
                    color=_C_BLOOD if rol == "vampir" else _C_NIGHT,
                ))
            except (discord.Forbidden, discord.HTTPException):
                dm_hatası.append(oyuncu.display_name)

        # Açılış mesajı (kanal)
        sayım = Counter(roller_listesi)
        rol_satır = " · ".join(
            f"{ROL_EMOJI[r]} **{sayım[r]}**"
            for r in _ROL_SIRA if r in sayım
        )
        oyuncu_satırları = "\n".join(f"🪑 {o.mention}" for o in self.oyuncular)

        items: list[dict] = [
            c_section(
                c_text("## 🧛 Vampir Köylü Başladı!"),
                accessory=c_thumbnail(str(self.kurucu.display_avatar.url)),
            ),
            c_separator(),
            c_text(
                f"**🧑‍🤝‍🧑 Oyuncular ({len(self.oyuncular)})**\n{oyuncu_satırları}"
            ),
            c_separator(),
            c_text(f"**🎭 Rol Dağılımı**\n{rol_satır}"),
            c_separator(),
            c_text(
                f"**📜 Faz Akışı**\n"
                f"🌙 **Gece** → Vampirler kurban seçer · Doktor korur · Kahin rol öğrenir\n"
                f"☀️ **Gündüz** → Tartış ve oy ver, birini idam et\n\n"
                f"**🏆 Galibiyet**\n"
                f"👨‍🌾 Köylüler: Tüm vampirleri bul\n"
                f"🧛 Vampirler: Köylülerle eşit/daha fazla ol"
            ),
        ]
        if kanal_acildi and self.vampir_kanal:
            items.append(c_separator())
            items.append(c_text(f"-# 🩸 Bu oyunda **{self._vampir_sayısı()} vampir** var — onlara özel **{self.vampir_kanal.mention}** kanalı açıldı."))
        if dm_hatası:
            items.append(c_separator())
            items.append(c_text(f"⚠️ **DM gönderilemedi:** {', '.join(dm_hatası)}"))
        items.append(c_separator())
        items.append(c_text(f"-# 📬 Roller DM ile gönderildi · Oyun {self.gece_sayısı + 1}. gecede başlıyor..."))

        await channel_send(self.kanal, c_container(*items, color=_C_BLOOD))
        await asyncio.sleep(5)
        await self._gece_başlat()

    async def _gece_başlat(self):
        self.gece_sayısı += 1
        self.vampir_oyları.clear()
        self.doktor_koruması = None
        self.kahin_görevi    = None
        self.gece_tamamlayanlar.clear()
        self._gece_cozuluyor = False

        # Vampir kanalına gece bilgisi
        if self.vampir_kanal:
            try:
                yaşayan_olmayan_vampirler = [o for o in self.yaşayanlar if self.roller[o.id] != "vampir"]
                hedef_listesi = "\n".join(f"💀 {o.display_name}" for o in yaşayan_olmayan_vampirler)
                await channel_send(self.vampir_kanal, c_container(
                    c_text(f"## 🌙 {self.gece_sayısı}. Gece Başladı"),
                    c_separator(),
                    c_text(f"**🎯 Olası Hedefler**\n{hedef_listesi or '_Hedef yok._'}"),
                    c_separator(),
                    c_text("-# Hedefte anlaşın, sonra ana kanaldan oyu kullanın."),
                    color=_C_BLOOD,
                ))
            except Exception:
                pass

        yaşayanlar_str = "\n".join(f"🪑 {o.mention}" for o in self.yaşayanlar)

        gece_kart = c_container(
            c_section(
                c_text(f"## 🌙 {self.gece_sayısı}. Gece\n-# Köy uykuya dalıyor..."),
                accessory=c_thumbnail(str(self.kanal.guild.icon.url) if self.kanal.guild and self.kanal.guild.icon else str(self.kurucu.display_avatar.url)),
            ),
            c_separator(),
            c_text(
                f"**🎭 Roller bu gece eyleme geçer**\n"
                f"🧛 **Vampirler** kurban seçer\n"
                f"👨‍⚕️ **Doktor** birini korur\n"
                f"🔮 **Kahin** rol öğrenir\n"
                f"👨‍🌾 **Köylüler** uyur 💤"
            ),
            c_separator(),
            c_text(f"**🪑 Hayatta Kalanlar ({len(self.yaşayanlar)})**\n{yaşayanlar_str}"),
            c_separator(),
            c_text(f"-# 🌙 Butona basıp gece eylemini seç · ⏱️ {GECE_SURESI}sn"),
            color=_C_NIGHT,
        )

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
            vote_counts = Counter(self.vampir_oyları.values())
            most_common = vote_counts.most_common()
            top_votes = most_common[0][1]
            # Tie handling: if multiple targets have equal top votes, randomize
            tied = [target_id for target_id, count in most_common if count == top_votes]
            kurban_id = random.choice(tied)

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

        yaşayanlar_str = "\n".join(f"🪑 {o.mention}" for o in self.yaşayanlar) or "_—_"

        # Guild icon yoksa kurucu avatarı fallback olur
        guild_icon = (
            str(self.kanal.guild.icon.url)
            if self.kanal.guild and self.kanal.guild.icon
            else str(self.kurucu.display_avatar.url)
        )
        if kurtarıldı:
            sabah_section = c_section(
                c_text("## 🌅 Sabah Oldu\n### 💉 Doktor Birini Kurtardı!"),
                accessory=c_thumbnail(guild_icon),
            )
            sabah_body = "Vampirler bir kurban seçti ama Doktor onu korudu — **kimse ölmedi!**"
            renk = COLORS.SUCCESS
        elif öldü:
            sabah_section = c_section(
                c_text(f"## 🌅 Sabah Oldu\n### 💀 {öldü.display_name} Öldü"),
                accessory=c_thumbnail(str(öldü.display_avatar.url)),
            )
            rol_str = f"{ROL_EMOJI.get(self.roller[öldü.id], '❓')} **{self.roller[öldü.id].capitalize()}**"
            sabah_body = f"💀 **{öldü.mention}** bu gece hayatını kaybetti.\n🎭 Gerçek rolü: {rol_str}"
            renk = _C_DAWN
        else:
            sabah_section = c_section(
                c_text("## 🌅 Sabah Oldu\n### 😴 Sessiz Bir Gece"),
                accessory=c_thumbnail(guild_icon),
            )
            sabah_body = "Bu gece kimse ölmedi."
            renk = _C_DAWN

        await channel_send(self.kanal, c_container(
            sabah_section,
            c_separator(),
            c_text(sabah_body),
            c_separator(),
            c_text(f"**🪑 Hayatta Kalanlar ({len(self.yaşayanlar)})**\n{yaşayanlar_str}"),
            color=renk,
        ))

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
            await channel_send(self.kanal, c_card(
                "## ⚖️ Oylar Eşit",
                body="Bu gündüz **kimse idam edilmedi** — vampirler şimdilik güvende.",
                color=0x95A5A6,
            ))
        elif not self.gunduz_oyları:
            await channel_send(self.kanal, c_card(
                "## 🤫 Kimse Oy Kullanmadı",
                body="Bu gündüz kimse idam edilmedi.",
                color=0x95A5A6,
            ))
        elif elenecek:
            # Oy detayı
            oy_detay: list[str] = []
            for voter_id, target_id in self.gunduz_oyları.items():
                voter  = self._bul(voter_id)
                target = self._bul(target_id)
                if voter and target:
                    oy_detay.append(f"┗ {voter.display_name} → **{target.display_name}**")

            rol_str = f"{ROL_EMOJI.get(self.roller[elenecek.id], '❓')} **{self.roller[elenecek.id].capitalize()}**"
            await channel_send(self.kanal, c_container(
                c_section(
                    c_text(f"## ⚖️ Mahkeme Kararı\n### 💀 {elenecek.display_name} İdam Edildi"),
                    accessory=c_thumbnail(str(elenecek.display_avatar.url)),
                ),
                c_separator(),
                c_text(f"🎭 **Gerçek Rolü:** {rol_str}"),
                c_separator(),
                c_text("**🗳️ Oy Dökümü**\n" + ("\n".join(oy_detay[:10]) if oy_detay else "_—_")),
                color=_C_BLOOD,
            ))

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

        avci_kart = c_container(
            c_section(
                c_text(f"## 🏹 Son Nefes!\n### {avcı.display_name} bir Avcıydı"),
                accessory=c_thumbnail(str(avcı.display_avatar.url)),
            ),
            c_separator(),
            c_text(f"💔 Son nefesinde **birini yanında götürebilir.**\n⏳ `{AVCI_SURESI}` saniye içinde seçim yap!"),
            color=_C_HUNTER,
        )

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
                rol_str = f"{ROL_EMOJI.get(self.roller[hedef.id], '❓')} **{self.roller[hedef.id].capitalize()}**"
                await channel_send(self.kanal, c_container(
                    c_section(
                        c_text(f"## 🏹 Avcının Son Oku\n### 💀 {hedef.display_name}"),
                        accessory=c_thumbnail(str(hedef.display_avatar.url)),
                    ),
                    c_separator(),
                    c_text(f"**{avcı.display_name}** son nefesinde {hedef.mention}'i yanında götürdü!\n🎭 Rolü: {rol_str}"),
                    color=_C_HUNTER,
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
    @app_commands.guild_only()
    async def vampirkoylu(self, interaction: discord.Interaction):
        view = VampirKoyluLobiView(interaction.user)  # type: ignore[arg-type]
        view.msg = await respond(interaction, *view._card(), view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(VampirKoylu(bot))
