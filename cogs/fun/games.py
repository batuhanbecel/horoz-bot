import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from ._shared import fun_embed, SEKIZ_TOP_YANIT

# ── Taş Kağıt Makas ────────────────────────────────────────────────────────────

_TKM_KAZANAN = {("taş", "makas"), ("makas", "kağıt"), ("kağıt", "taş")}
_TKM_EMOJI = {"taş": "🪨", "kağıt": "📄", "makas": "✂️"}


def _tkm_tur(s1: str, s2: str) -> str:
    if s1 == s2:
        return "berabere"
    return "1" if (s1, s2) in _TKM_KAZANAN else "2"


class TKMView(discord.ui.View):
    def __init__(self, oyuncu: discord.Member, rakip: discord.Member | None):
        super().__init__(timeout=60)
        self.oyuncu = oyuncu
        self.rakip = rakip
        self.seçimler: dict[int, str] = {}
        self.skor = [0, 0]
        self.tur = 1
        self.hedef = 2
        self.msg: discord.Message | None = None

    def _r_isim(self) -> str:
        return self.rakip.display_name if self.rakip else "Bot"

    def _r_mention(self) -> str:
        return self.rakip.mention if self.rakip else "**Bot**"

    def _embed(self, açıklama: str = "") -> discord.Embed:
        e = discord.Embed(
            title=f"🪨📄✂️ Taş Kağıt Makas — Tur {self.tur}",
            description=açıklama or "Seçiminizi yapın!",
            color=discord.Color.blue(),
        )
        e.add_field(name=self.oyuncu.display_name, value="⭐" * self.skor[0] or "—", inline=True)
        e.add_field(name="VS", value="⚔️", inline=True)
        e.add_field(name=self._r_isim(), value="⭐" * self.skor[1] or "—", inline=True)
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
        metin = f"{_TKM_EMOJI[s1]} **{s1}** vs {_TKM_EMOJI[s2]} **{s2}**\n"

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
            for c in self.children:
                c.disabled = True
            kazanan = self.oyuncu.mention if self.skor[0] > self.skor[1] else self._r_mention()
            metin += f"\n\n🏆 **{kazanan} oyunu kazandı!**"
            return await self.msg.edit(embed=self._embed(metin), view=self)

        self.tur += 1
        self.seçimler.clear()
        await self.msg.edit(
            embed=self._embed(metin + "\n\nSonraki tur için seçiminizi yapın!"),
            view=self,
        )

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await self.msg.edit(embed=self._embed("⏰ Süre doldu!"), view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Taş", emoji="🪨", style=discord.ButtonStyle.secondary)
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
    "KEDI", "KOPEK", "ASLAN", "KAPLAN", "FIL", "TIMSAH", "TAVSAN",
    "TAVUK", "BALIK", "KURBAGA", "KAPLUMBAGA", "KARTAL", "PAPAGAN",
    "ZEBRA", "KANGURU", "PENGUEN", "AHTAPOT", "SINCAP",
    # Eşyalar & Taşıtlar
    "MASA", "SANDALYE", "PENCERE", "KALEM", "KITAP", "TELEFON",
    "ARABA", "UCAK", "GEMI", "TREN", "BISIKLET", "HELIKOPTER", "ROKET",
    # Doğa
    "DENIZ", "ORMAN", "CICEK", "AGAC", "BULUT", "YILDIZ", "VOLKAN",
    "OKYANUS", "NEHIR", "GOL", "SEMA",
    # Yiyecek & İçecek
    "ELMA", "ARMUT", "PORTAKAL", "MUZ", "CILEK", "DOMATES",
    "PATATES", "EKMEK", "PEYNIR", "PIZZA", "BURGER",
    # Yerler
    "ISTANBUL", "ANKARA", "IZMIR", "OKUL", "HASTANE", "MARKET", "PLAJ",
    # Spor
    "FUTBOL", "BASKETBOL", "VOLEYBOL", "TENIS", "YUZME",
    # Teknoloji & Diğer
    "BILGISAYAR", "INTERNET", "MUZIK", "SINEMA", "TELEVIZYON",
    "SEHIR", "ULKE", "DUNYA", "UZAY", "GEZEGEN", "GALAKSI",
]


class HarfModal(discord.ui.Modal, title="Harf Tahmin Et"):
    harf = discord.ui.TextInput(
        label="Bir harf gir (A-Z)",
        min_length=1,
        max_length=1,
        placeholder="Örn: A",
    )

    def __init__(self, view: "AdamAsmacaView"):
        super().__init__()
        self._game = view

    async def on_submit(self, interaction: discord.Interaction):
        await self._game.harf_tahmin(interaction, self.harf.value.upper())


class AdamAsmacaView(discord.ui.View):
    def __init__(self, oyuncu: discord.Member, kelime: str):
        super().__init__(timeout=300)
        self.oyuncu = oyuncu
        self.kelime = kelime
        self.tahminler: set[str] = set()
        self.yanlis = 0
        self.maks = 6
        self.msg: discord.Message | None = None

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

    def _bitir(self):
        self.stop()
        for c in self.children:
            c.disabled = True

    async def harf_tahmin(self, interaction: discord.Interaction, harf: str):
        if interaction.user.id != self.oyuncu.id:
            return await interaction.response.send_message("Bu oyun sana ait değil!", ephemeral=True)
        if not harf.isalpha():
            return await interaction.response.send_message("Geçersiz karakter!", ephemeral=True)
        if harf in self.tahminler:
            return await interaction.response.send_message(f"`{harf}` zaten tahmin edildi!", ephemeral=True)

        self.tahminler.add(harf)
        if harf not in self.kelime:
            self.yanlis += 1

        await interaction.response.defer()

        if self._bitti():
            self._bitir()
            e = self._embed("🎉 Adam Asmaca — Kazandın!", discord.Color.green(), f"Kelime: **`{self.kelime}`**")
            return await self.msg.edit(embed=e, view=self)

        if self.yanlis >= self.maks:
            self._bitir()
            e = self._embed("💀 Adam Asmaca — Kaybettin!", discord.Color.red(), f"Kelime: **`{self.kelime}`** idi.")
            return await self.msg.edit(embed=e, view=self)

        await self.msg.edit(embed=self._embed(), view=self)

    async def on_timeout(self):
        self._bitir()
        if self.msg:
            try:
                e = self._embed("⏰ Adam Asmaca — Süre Doldu!", discord.Color.red(), f"Kelime: **`{self.kelime}`** idi.")
                await self.msg.edit(embed=e, view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Harf Tahmin Et", emoji="✏️", style=discord.ButtonStyle.primary)
    async def tahmin_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_modal(HarfModal(self))

    @discord.ui.button(label="Vazgeç", emoji="🏳️", style=discord.ButtonStyle.danger)
    async def vazgeç_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.oyuncu.id:
            return await interaction.response.send_message("Bu oyun sana ait değil!", ephemeral=True)
        self._bitir()
        e = self._embed("🏳️ Adam Asmaca — Teslim Oldun!", discord.Color.red(), f"Kelime: **`{self.kelime}`** idi.")
        await interaction.response.edit_message(embed=e, view=self)


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


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
