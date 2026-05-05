import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from ._shared import fun_embed, SEKIZ_TOP_YANIT

# ── Taş Kağıt Makas ────────────────────────────────────────────────────────────

_TKM_KAZANAN = {("taş", "makas"), ("makas", "kağıt"), ("kağıt", "taş")}
_TKM_EMOJI   = {"taş": "🪨", "kağıt": "📄", "makas": "✂️"}
_TKM_LABEL   = {"taş": "Taş", "kağıt": "Kağıt", "makas": "Makas"}


def _tkm_tur(s1: str, s2: str) -> str:
    if s1 == s2:
        return "berabere"
    return "1" if (s1, s2) in _TKM_KAZANAN else "2"


class TKMTekrarView(discord.ui.View):
    def __init__(self, oyuncu: discord.Member, rakip: discord.Member | None):
        super().__init__(timeout=120)
        self.oyuncu = oyuncu
        self.rakip  = rakip
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
        allowed = {self.oyuncu.id}
        if self.rakip:
            allowed.add(self.rakip.id)
        if interaction.user.id not in allowed:
            return await interaction.response.send_message("Bu oyuna dahil değilsin!", ephemeral=True)
        btn.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)
        view = TKMView(self.oyuncu, self.rakip)
        r_str = self.rakip.mention if self.rakip else "Bot"
        msg = await interaction.channel.send(
            embed=view._embed(f"{self.oyuncu.mention} vs {r_str}\n\nSeçiminizi yapın!"),
            view=view,
        )
        view.msg = msg


class TKMView(discord.ui.View):
    def __init__(self, oyuncu: discord.Member, rakip: discord.Member | None):
        super().__init__(timeout=60)
        self.oyuncu  = oyuncu
        self.rakip   = rakip
        self.seçimler: dict[int, str] = {}
        self.skor    = [0, 0]
        self.tur     = 1
        self.hedef   = 2
        self.msg: discord.Message | None = None

    def _r_isim(self)    -> str: return self.rakip.display_name if self.rakip else "Bot"
    def _r_mention(self) -> str: return self.rakip.mention if self.rakip else "**Bot**"

    def _embed(self, açıklama: str = "") -> discord.Embed:
        s0 = "⭐" * self.skor[0] if self.skor[0] else "—"
        s1 = "⭐" * self.skor[1] if self.skor[1] else "—"
        e = discord.Embed(
            title=f"🪨📄✂️ Taş Kağıt Makas",
            color=discord.Color.blue(),
        )
        e.add_field(name=f"👤 {self.oyuncu.display_name}", value=s0, inline=True)
        e.add_field(name=f"Tur {self.tur}",               value="⚔️", inline=True)
        e.add_field(name=f"👤 {self._r_isim()}",          value=s1,   inline=True)
        e.add_field(name="​", value=açıklama or "Seçiminizi yapın!", inline=False)
        e.set_footer(text=f"İlk {self.hedef} galibiyeti alan kazanır!")
        e.timestamp = discord.utils.utcnow()
        return e

    async def _oyna(self, interaction: discord.Interaction, seçim: str):
        uid = interaction.user.id

        if self.rakip:
            if uid not in (self.oyuncu.id, self.rakip.id):
                return await interaction.response.send_message("Bu oyunda oynayamazsın!", ephemeral=True)
            if uid in self.seçimler:
                return await interaction.response.send_message("Bu turda zaten seçim yaptın!", ephemeral=True)
            self.seçimler[uid] = seçim
            await interaction.response.defer()
            if len(self.seçimler) < 2:
                beklenen = self.rakip if uid == self.oyuncu.id else self.oyuncu
                return await self.msg.edit(embed=self._embed(
                    f"{interaction.user.mention} seçimini yaptı.\n{beklenen.mention} bekleniyor..."
                ))
            s1 = self.seçimler[self.oyuncu.id]
            s2 = self.seçimler[self.rakip.id]
        else:
            if uid != self.oyuncu.id:
                return await interaction.response.send_message("Bu oyun sana ait değil!", ephemeral=True)
            if uid in self.seçimler:
                return await interaction.response.send_message("Bu turda zaten seçim yaptın!", ephemeral=True)
            s1 = seçim
            s2 = random.choice(["taş", "kağıt", "makas"])
            self.seçimler[uid] = s1
            await interaction.response.defer()

        sonuç = _tkm_tur(s1, s2)
        l1, l2 = _TKM_LABEL[s1], _TKM_LABEL[s2]
        metin = f"{_TKM_EMOJI[s1]} **{l1}** vs {_TKM_EMOJI[s2]} **{l2}**\n"

        if sonuç == "berabere":
            metin += "🤝 **Bu tur berabere!**"
        elif sonuç == "1":
            self.skor[0] += 1
            metin += f"✅ **{self.oyuncu.display_name} bu turu kazandı!**"
        else:
            self.skor[1] += 1
            metin += f"✅ **{self._r_isim()} bu turu kazandı!**"

        if self.skor[0] >= self.hedef or self.skor[1] >= self.hedef:
            self.stop()
            kazanan = self.oyuncu.mention if self.skor[0] > self.skor[1] else self._r_mention()
            metin += f"\n\n🏆 **{kazanan} oyunu kazandı!**"
            tekrar = TKMTekrarView(self.oyuncu, self.rakip)
            assert self.msg
            await self.msg.edit(embed=self._embed(metin), view=tekrar)
            tekrar.msg = self.msg
            return

        self.tur += 1
        self.seçimler.clear()
        assert self.msg
        await self.msg.edit(embed=self._embed(metin + "\n\nSonraki tur için seçiminizi yapın!"), view=self)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await self.msg.edit(embed=self._embed("⏰ Süre doldu!"), view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Taş",   emoji="🪨", style=discord.ButtonStyle.secondary)
    async def taş_btn(self, i: discord.Interaction, _: discord.ui.Button):
        await self._oyna(i, "taş")

    @discord.ui.button(label="Kağıt", emoji="📄", style=discord.ButtonStyle.secondary)
    async def kağıt_btn(self, i: discord.Interaction, _: discord.ui.Button):
        await self._oyna(i, "kağıt")

    @discord.ui.button(label="Makas", emoji="✂️", style=discord.ButtonStyle.secondary)
    async def makas_btn(self, i: discord.Interaction, _: discord.ui.Button):
        await self._oyna(i, "makas")


# ── Adam Asmaca ────────────────────────────────────────────────────────────────

_AŞAMALAR = [
    "```\n  -----\n  |   |\n  |\n  |\n  |\n  |\n------\n```",
    "```\n  -----\n  |   |\n  |   O\n  |\n  |\n  |\n------\n```",
    "```\n  -----\n  |   |\n  |   O\n  |   |\n  |\n  |\n------\n```",
    "```\n  -----\n  |   |\n  |   O\n  |  /|\n  |\n  |\n------\n```",
    "```\n  -----\n  |   |\n  |   O\n  |  /|\\\n  |\n  |\n------\n```",
    "```\n  -----\n  |   |\n  |   O\n  |  /|\\\n  |  /\n  |\n------\n```",
    "```\n  -----\n  |   |\n  |   O\n  |  /|\\\n  |  / \\\n  |\n------\n```",
]

_KELIMELER = [
    # Hayvanlar
    "KEDİ", "KÖPEK", "ASLAN", "KAPLAN", "FİL", "TİMSAH", "TAVŞAN",
    "TAVUK", "BALIK", "KURBAĞA", "KAPLUMBAĞA", "KARTAL", "PAPAĞAN",
    "ZEBRA", "KANGURU", "PENGUEN", "AHTAPOT", "SINCAP",
    # Eşyalar & Taşıtlar
    "MASA", "SANDALYE", "PENCERE", "KALEM", "KİTAP", "TELEFON",
    "ARABA", "UÇAK", "GEMİ", "TREN", "BİSİKLET", "HELİKOPTER", "ROKET",
    # Doğa
    "DENİZ", "ORMAN", "ÇİÇEK", "AĞAÇ", "BULUT", "YILDIZ", "VOLKAN",
    "OKYANUS", "NEHİR", "GÖL",
    # Yiyecek
    "ELMA", "ARMUT", "PORTAKAL", "MUZ", "ÇİLEK", "DOMATES",
    "PATATES", "EKMEK", "PEYNİR", "PİZZA",
    # Yerler
    "İSTANBUL", "ANKARA", "İZMİR", "OKUL", "HASTANE", "MARKET", "PLAJ",
    # Spor & Teknoloji
    "FUTBOL", "BASKETBOL", "VOLEYBOL", "TENİS", "YÜZME",
    "BİLGİSAYAR", "İNTERNET", "MÜZİK", "SİNEMA", "TELEVİZYON",
    # Diğer
    "ŞEHİR", "ÜLKE", "DÜNYA", "UZAY", "GEZEGEN", "GALAKSİ",
]

# Turkish I/İ normalization: dotted vs dotless confusion
_TR_NORM: dict[str, str] = {"I": "İ", "İ": "I"}


class HarfModal(discord.ui.Modal, title="Harf Tahmin Et"):
    harf = discord.ui.TextInput(
        label="Bir harf gir",
        min_length=1,
        max_length=1,
        placeholder="Örn: K, Ö, Ş ...",
    )

    def __init__(self, view: "AdamAsmacaView"):
        super().__init__()
        self._game = view

    async def on_submit(self, interaction: discord.Interaction):
        await self._game.harf_tahmin(interaction, self.harf.value.upper())


class KelimeModal(discord.ui.Modal):
    kelime = discord.ui.TextInput(
        label="Kelimeyi yaz",
        min_length=1,
        max_length=30,
        placeholder="Tam kelimeyi gir...",
    )

    def __init__(self, view: "AdamAsmacaView"):
        super().__init__(title="Kelime Tahmin Et")
        self._game = view

    async def on_submit(self, interaction: discord.Interaction):
        await self._game.kelime_tahmin(interaction, self.kelime.value.strip().upper())


class AdamAsmacaTekrarView(discord.ui.View):
    def __init__(self, oyuncu: discord.Member):
        super().__init__(timeout=120)
        self.oyuncu = oyuncu
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
        if interaction.user.id != self.oyuncu.id:
            return await interaction.response.send_message("Bu oyun sana ait değil!", ephemeral=True)
        btn.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)
        kelime = random.choice(_KELIMELER)
        view = AdamAsmacaView(self.oyuncu, kelime)
        msg = await interaction.channel.send(embed=view._embed(), view=view)
        view.msg = msg


class AdamAsmacaView(discord.ui.View):
    def __init__(self, oyuncu: discord.Member, kelime: str):
        super().__init__(timeout=300)
        self.oyuncu   = oyuncu
        self.kelime   = kelime
        self.tahminler: set[str] = set()
        self.yanlis   = 0
        self.maks     = 6
        self.msg: discord.Message | None = None

    def _normalize_harf(self, harf: str) -> str:
        alt = _TR_NORM.get(harf)
        if alt and alt in self.kelime and harf not in self.kelime:
            return alt
        return harf

    def _gizli(self) -> str:
        return " ".join(h if h in self.tahminler else "_" for h in self.kelime)

    def _embed(
        self,
        başlık: str = "🪢 Adam Asmaca",
        renk: discord.Color = discord.Color.orange(),
        son_not: str = "",
    ) -> discord.Embed:
        e = discord.Embed(
            title=başlık,
            description=(
                f"{_AŞAMALAR[self.yanlis]}\n"
                f"**Kelime:** `{self._gizli()}`\n"
                f"**Yanlış:** {self.yanlis}/{self.maks}"
                + (f"\n\n{son_not}" if son_not else "")
            ),
            color=renk,
        )
        if self.tahminler:
            e.add_field(name="Tahmin Edilenler", value=" ".join(sorted(self.tahminler)))
        e.set_footer(text=f"Oynayan: {self.oyuncu.display_name}")
        e.timestamp = discord.utils.utcnow()
        return e

    def _bitti(self) -> bool:
        return all(h in self.tahminler for h in self.kelime)

    async def _oyun_bitti(self, embed: discord.Embed):
        self.stop()
        tekrar = AdamAsmacaTekrarView(self.oyuncu)
        assert self.msg
        await self.msg.edit(embed=embed, view=tekrar)
        tekrar.msg = self.msg

    async def harf_tahmin(self, interaction: discord.Interaction, harf: str):
        if interaction.user.id != self.oyuncu.id:
            return await interaction.response.send_message("Bu oyun sana ait değil!", ephemeral=True)
        if not harf.isalpha():
            return await interaction.response.send_message("Geçersiz karakter!", ephemeral=True)
        if harf in self.tahminler:
            return await interaction.response.send_message(f"`{harf}` zaten tahmin edildi!", ephemeral=True)

        harf = self._normalize_harf(harf)
        self.tahminler.add(harf)
        if harf not in self.kelime:
            self.yanlis += 1

        await interaction.response.defer()
        assert self.msg

        if self._bitti():
            e = self._embed("🎉 Adam Asmaca — Kazandın!", discord.Color.green(), f"Kelime: **`{self.kelime}`**")
            return await self._oyun_bitti(e)
        if self.yanlis >= self.maks:
            e = self._embed("💀 Adam Asmaca — Kaybettin!", discord.Color.red(), f"Kelime: **`{self.kelime}`** idi.")
            return await self._oyun_bitti(e)

        await self.msg.edit(embed=self._embed(), view=self)

    async def kelime_tahmin(self, interaction: discord.Interaction, tahmin: str):
        if interaction.user.id != self.oyuncu.id:
            return await interaction.response.send_message("Bu oyun sana ait değil!", ephemeral=True)

        await interaction.response.defer()
        assert self.msg

        if tahmin == self.kelime:
            for h in self.kelime:
                self.tahminler.add(h)
            e = self._embed("🎉 Adam Asmaca — Kazandın!", discord.Color.green(), f"Kelime: **`{self.kelime}`**")
            return await self._oyun_bitti(e)

        # Wrong word guess = 2 yanlış cezası
        self.yanlis = min(self.yanlis + 2, self.maks)
        if self.yanlis >= self.maks:
            e = self._embed("💀 Adam Asmaca — Kaybettin!", discord.Color.red(), f"Kelime: **`{self.kelime}`** idi.")
            return await self._oyun_bitti(e)

        e = self._embed(son_not=f"❌ **`{tahmin}`** yanlış! 2 hak kaybettin.")
        await self.msg.edit(embed=e, view=self)

    async def on_timeout(self):
        self.stop()
        if self.msg:
            try:
                e = self._embed("⏰ Adam Asmaca — Süre Doldu!", discord.Color.red(), f"Kelime: **`{self.kelime}`** idi.")
                tekrar = AdamAsmacaTekrarView(self.oyuncu)
                await self.msg.edit(embed=e, view=tekrar)
                tekrar.msg = self.msg
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Harf Tahmin Et",   emoji="✏️", style=discord.ButtonStyle.primary)
    async def tahmin_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(HarfModal(self))

    @discord.ui.button(label="Kelime Tahmin Et", emoji="💬", style=discord.ButtonStyle.primary)
    async def kelime_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(KelimeModal(self))

    @discord.ui.button(label="Vazgeç", emoji="🏳️", style=discord.ButtonStyle.danger)
    async def vazgeç_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.oyuncu.id:
            return await interaction.response.send_message("Bu oyun sana ait değil!", ephemeral=True)
        self.stop()
        e = self._embed("🏳️ Adam Asmaca — Teslim Oldun!", discord.Color.red(), f"Kelime: **`{self.kelime}`** idi.")
        tekrar = AdamAsmacaTekrarView(self.oyuncu)
        await interaction.response.edit_message(embed=e, view=tekrar)
        tekrar.msg = interaction.message


# ── Cog ────────────────────────────────────────────────────────────────────────

class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="yazıtura", description="Yazı mı tura mı? Bozuk para atar.")
    async def yazıtura(self, interaction: discord.Interaction):
        await interaction.response.defer()
        sonuç = random.choice(["Yazı", "Tura"])
        spin_embed = discord.Embed(
            title="Para atılıyor...",
            description=f"{interaction.user.mention} parayı havaya fırlattı!\n\n<a:spinning_para:1500895448968331468>",
            color=discord.Color.gold(),
        )
        spin_embed.timestamp = discord.utils.utcnow()
        msg = await interaction.followup.send(embed=spin_embed, wait=True)
        await asyncio.sleep(2)
        if sonuç == "Tura":
            emoji_str, title, color = "<:tura:1500895527242563837>", "Tura!", discord.Color.gold()
        else:
            emoji_str, title, color = "<:yazi:1500895591129944194>", "Yazı!", discord.Color.light_grey()
        result_embed = discord.Embed(
            title=title,
            description=f"{interaction.user.mention} parayı attı ve...\n\n{emoji_str}  **{sonuç}** çıktı!",
            color=color,
        )
        result_embed.timestamp = discord.utils.utcnow()
        await msg.edit(embed=result_embed)

    @app_commands.command(name="zar", description="Zar atar.")
    @app_commands.describe(yüz="Zarın kaç yüzlü olduğu (varsayılan 6)", adet="Kaç zar atılsın (1-10)")
    async def zar(
        self,
        interaction: discord.Interaction,
        yüz: app_commands.Range[int, 2, 100] = 6,
        adet: app_commands.Range[int, 1, 10] = 1,
    ):
        sonuçlar = [random.randint(1, yüz) for _ in range(adet)]
        toplam = sum(sonuçlar)
        sonuç_str = " + ".join(f"**{s}**" for s in sonuçlar)
        embed = fun_embed("🎲 Zar Atıldı!", f"{adet}d{yüz}: {sonuç_str}\n**Toplam: {toplam}**", discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="8top", description="Sihirli 8-top'a bir soru sor.")
    @app_commands.describe(soru="Sormak istediğin soru")
    async def sekiz_top(self, interaction: discord.Interaction, soru: str):
        yanıt = random.choice(SEKIZ_TOP_YANIT)
        embed = fun_embed("🎱 Sihirli 8-Top", f"**Soru:** {soru}\n\n**Cevap:** {yanıt}", discord.Color.dark_blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tkm", description="Taş Kağıt Makas — ilk 2 galibiyeti alan kazanır.")
    @app_commands.describe(rakip="Rakip (boş bırakırsan bota karşı oynarsın)")
    async def tkm(self, interaction: discord.Interaction, rakip: discord.Member | None = None):
        if rakip and rakip.id == interaction.user.id:
            return await interaction.response.send_message("Kendinle oynayamazsın!", ephemeral=True)
        if rakip and rakip.bot:
            return await interaction.response.send_message("Botlarla oynayamazsın!", ephemeral=True)
        view = TKMView(interaction.user, rakip)
        r_str = rakip.mention if rakip else "Bot"
        await interaction.response.send_message(
            embed=view._embed(f"{interaction.user.mention} vs {r_str}\n\nSeçiminizi yapın!"),
            view=view,
        )
        view.msg = await interaction.original_response()

    @app_commands.command(name="adamasmaca", description="Adam Asmaca — kelimeyi tahmin et.")
    async def adamasmaca(self, interaction: discord.Interaction):
        kelime = random.choice(_KELIMELER)
        view = AdamAsmacaView(interaction.user, kelime)
        await interaction.response.send_message(embed=view._embed(), view=view)
        view.msg = await interaction.original_response()

    @app_commands.command(name="kaccm", description="Pipi ölçer. Bilimsel kesinlik garantili.")
    @app_commands.describe(kişi="Ölçülecek kişi (boş = kendin)")
    async def kaccm(self, interaction: discord.Interaction, kişi: discord.Member | None = None):
        hedef = kişi or interaction.user
        cm = random.randint(1, 35)

        if cm < 5:
            emoji = "🤏"
            bar   = "8" + "." * cm + "D"
            gif   = "https://tenor.com/pGMLgI9r1XT.gif"
            yorum = random.choice([
                "Ciğer bu iş böyle olmaz...",
                "Yok gibi ama var işte, maşallah",
                "Minyatür sanat eseri sayılır",
                "Kaybedersin onu bir gün farkında bile olmazsın",
            ])
        elif cm < 10:
            emoji = "😐"
            bar   = "8" + "-" * cm + "D"
            gif   = "https://tenor.com/dxoyIB0zYGP.gif"
            yorum = random.choice([
                "Yani... çalışıyor en azından",
                "Eh, yoksulluğun utanacak bir yanı yok",
                "Kimseye söyleme, sırrın saklı",
                "Ortalama altı ama gurur duyabilirsin herhalde",
            ])
        elif cm < 15:
            emoji = "😎"
            bar   = "8" + "=" * cm + "D"
            gif   = "https://tenor.com/bXq2c.gif"
            yorum = random.choice([
                "Tıkırında, ne eksik ne fazla",
                "Standart paket, fabrika çıkışı",
                "İşi görür, kimse şikayet etmez",
                "Normal insan işte, tebrikler",
            ])
        elif cm < 20:
            emoji = "🔥"
            bar   = "8" + "=" * cm + "D"
            gif   = "https://tenor.com/ukUQgPg9ond.gif"
            yorum = random.choice([
                "E iyimiş be abi, kimden aldın bunu",
                "Sormak istemiyorum ama nasıl taşıyorsun",
                "Arkadaşlarına söyleme kıskanırlar",
                "Oha be, adam gibi adam çıktın",
            ])
        elif cm < 30:
            emoji = "🚀"
            bar   = "8" + "=" * 22 + "D 🚀"
            gif   = "https://tenor.com/bwVKu.gif"
            yorum = random.choice([
                "OHAAA KAMIŞA BAK LAN",
                "Tarzan mı büyüttü seni kardeşim",
                "Bununla mı geziyorsun her gün, nasıl sığıyor",
                "Saygıyla eğiliyorum, devam et",
            ])
        else:
            emoji = "💀"
            bar   = "8" + "=" * 30 + "D 💀"
            gif   = "https://tenor.com/bGiZT.gif"
            yorum = random.choice([
                "Kardeş bu silah ruhsatı istiyor",
                "Hastane acil servis alarma geçsin",
                "Bu bir pipi değil bu bir altyapı projesi",
                "Devlet senden haberdar mı, ihbar etmem lazım",
            ])

        embed = discord.Embed(
            title=f"{emoji} Bilimsel Pipi Ölçümü™",
            description=f"{hedef.mention} — **{cm} cm**\n`{bar}`\n\n💬 {yorum}",
            color=discord.Color.from_rgb(255, 105, 180),
        )
        embed.set_thumbnail(url=hedef.display_avatar.url)
        embed.set_footer(text="Horoz Bot Ölçüm Laboratuvarı™ • Sonuçlar yüzde yüz bilimseldir")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(content=gif, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
