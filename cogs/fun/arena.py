import discord
from discord import app_commands
from discord.ext import commands
import random
from ._shared import fun_embed

# ── Hasar Hesaplama ─────────────────────────────────────────────────────────────
# Eylemler: "kılıç" | "büyü" | "kalkan"
# Kılıç:  20-35 dmg, %100 isabet, Kalkan tamamen bloklar
# Büyü:   30-45 dmg, %80 isabet, Kalkan'ı %55 oranında deler
# Kalkan: Kılıcı tamamen engeller, büyüden %55 azaltır

_EYLEM_EMOJI = {"kılıç": "⚔️", "büyü": "🔮", "kalkan": "🛡️"}
_EYLEM_LABEL = {"kılıç": "Kılıç", "büyü": "Büyü", "kalkan": "Kalkan"}

MAKS_HP   = 150
MAKS_TUR  = 20


def _hasar(saldirgan: str, savunmaci: str) -> tuple[int, str]:
    """Saldırganın eylemi → savunmacıya verilen (hasar, açıklama)."""
    if saldirgan == "kalkan":
        return 0, ""

    if saldirgan == "kılıç":
        if savunmaci == "kalkan":
            return 0, "🛡️ Kalkan engelledi!"
        dmg = random.randint(20, 35)
        if random.random() < 0.15:
            dmg = int(dmg * 1.6)
            return dmg, f"⚡ Kritik Kılıç! **{dmg}** hasar"
        return dmg, f"⚔️ Kılıç **{dmg}** hasar verdi"

    # büyü
    if random.random() > 0.80:
        return 0, "🔮 Büyü ıskaldı!"
    dmg = random.randint(30, 45)
    if savunmaci == "kalkan":
        dmg = int(dmg * 0.45)
        return dmg, f"🛡️ Kalkan büyüyü hafifletti → **{dmg}** hasar"
    if random.random() < 0.12:
        dmg = int(dmg * 1.6)
        return dmg, f"⚡ Kritik Büyü! **{dmg}** hasar"
    return dmg, f"🔮 Büyü **{dmg}** hasar verdi"


def _hp_bar(hp: int) -> str:
    hp = max(0, hp)
    filled = round(hp / MAKS_HP * 12)
    bar = "█" * filled + "░" * (12 - filled)
    return f"`{bar}` **{hp}/{MAKS_HP}**"


# ── Tekrar Oyna ─────────────────────────────────────────────────────────────────

class ArenaTekrarView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=120)
        self.p1 = p1
        self.p2 = p2
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
        if interaction.user.id not in (self.p1.id, self.p2.id):
            return await interaction.response.send_message("Bu oyuna dahil değilsin!", ephemeral=True)
        btn.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)
        view = ArenaView(self.p1, self.p2)
        msg = await interaction.channel.send(embed=view._embed(), view=view)
        view.msg = msg


# ── Ana Oyun View ────────────────────────────────────────────────────────────────

class ArenaView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=90)
        self.oyuncular = [p1, p2]
        self.hp        = [MAKS_HP, MAKS_HP]
        self.seçimler: dict[int, str] = {}
        self.tur       = 1
        self.log: list[str] = []
        self.msg: discord.Message | None = None

    def _embed(self, son_log: str = "") -> discord.Embed:
        p1, p2 = self.oyuncular
        e = discord.Embed(
            title=f"⚔️ Arena Dövüşü — Tur {self.tur}/{MAKS_TUR}",
            color=discord.Color.dark_red(),
        )
        e.add_field(
            name=f"❤️ {p1.display_name}",
            value=_hp_bar(self.hp[0]),
            inline=False,
        )
        e.add_field(
            name=f"❤️ {p2.display_name}",
            value=_hp_bar(self.hp[1]),
            inline=False,
        )
        if son_log:
            e.add_field(name=f"Tur {self.tur - 1} Özeti", value=son_log, inline=False)

        beklenenler = []
        for idx, oyuncu in enumerate(self.oyuncular):
            if oyuncu.id in self.seçimler:
                beklenenler.append(f"✅ {oyuncu.display_name}")
            else:
                beklenenler.append(f"⏳ {oyuncu.display_name}")
        e.add_field(name="Durum", value="\n".join(beklenenler), inline=False)
        e.set_footer(text="Eylemini seç • Kılıç: güvenli | Büyü: güçlü | Kalkan: savunma")
        e.timestamp = discord.utils.utcnow()
        return e

    async def _eylem_seç(self, interaction: discord.Interaction, eylem: str):
        uid = interaction.user.id
        if uid not in (self.oyuncular[0].id, self.oyuncular[1].id):
            return await interaction.response.send_message("Bu dövüşe dahil değilsin!", ephemeral=True)
        if uid in self.seçimler:
            return await interaction.response.send_message("Bu tur için zaten seçim yaptın!", ephemeral=True)

        self.seçimler[uid] = eylem
        await interaction.response.send_message(
            f"{_EYLEM_EMOJI[eylem]} **{_EYLEM_LABEL[eylem]}** seçildi! Rakip bekleniyor...",
            ephemeral=True,
        )

        assert self.msg
        await self.msg.edit(embed=self._embed())

        if len(self.seçimler) < 2:
            return

        # ── Her iki oyuncu da seçti → turu çöz ─────────────────────────────
        e1 = self.seçimler[self.oyuncular[0].id]
        e2 = self.seçimler[self.oyuncular[1].id]

        d_on_p2, acik2 = _hasar(e1, e2)
        d_on_p1, acik1 = _hasar(e2, e1)

        self.hp[0] = max(0, self.hp[0] - d_on_p1)
        self.hp[1] = max(0, self.hp[1] - d_on_p2)

        p1n, p2n = self.oyuncular[0].display_name, self.oyuncular[1].display_name
        log_satirlari = [
            f"**{p1n}** → {_EYLEM_EMOJI[e1]} {_EYLEM_LABEL[e1]}   |   "
            f"**{p2n}** → {_EYLEM_EMOJI[e2]} {_EYLEM_LABEL[e2]}",
        ]
        if acik2:
            log_satirlari.append(f"• {p1n}: {acik2}")
        if acik1:
            log_satirlari.append(f"• {p2n}: {acik1}")
        son_log = "\n".join(log_satirlari)

        self.tur += 1
        self.seçimler.clear()

        # ── Oyun bitti mi? ───────────────────────────────────────────────────
        bitti = self.hp[0] <= 0 or self.hp[1] <= 0 or self.tur > MAKS_TUR
        if bitti:
            self.stop()
            for c in self.children:
                c.disabled = True

            if self.hp[0] <= 0 and self.hp[1] <= 0:
                başlık, renk = "⚔️ Berabere! İkiniz de yıkıldınız.", discord.Color.greyple()
            elif self.hp[0] <= 0:
                başlık, renk = f"💀 {p2n} kazandı!", discord.Color.green()
            elif self.hp[1] <= 0:
                başlık, renk = f"💀 {p1n} kazandı!", discord.Color.green()
            else:
                kazanan = p1n if self.hp[0] > self.hp[1] else p2n
                başlık, renk = f"⏱️ Süre bitti! {kazanan} daha fazla HP'yle kazandı.", discord.Color.gold()

            e = discord.Embed(title=başlık, color=renk)
            e.add_field(name=f"❤️ {p1n}", value=_hp_bar(self.hp[0]), inline=False)
            e.add_field(name=f"❤️ {p2n}", value=_hp_bar(self.hp[1]), inline=False)
            e.add_field(name=f"Son Tur", value=son_log, inline=False)
            e.timestamp = discord.utils.utcnow()

            tekrar = ArenaTekrarView(self.oyuncular[0], self.oyuncular[1])
            await self.msg.edit(embed=e, view=tekrar)
            tekrar.msg = self.msg
            return

        await self.msg.edit(embed=self._embed(son_log), view=self)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                e = self._embed("⏰ Süre doldu, dövüş iptal!")
                e.color = discord.Color.greyple()
                await self.msg.edit(embed=e, view=self)
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
    async def arena(self, interaction: discord.Interaction, rakip: discord.Member):
        if rakip.id == interaction.user.id:
            return await interaction.response.send_message("Kendinle dövüşemezsin!", ephemeral=True)
        if rakip.bot:
            return await interaction.response.send_message("Botlarla dövüşemezsin!", ephemeral=True)

        p1   = interaction.user
        view = ArenaView(p1, rakip)
        e    = view._embed()
        e.description = (
            f"⚔️ **{p1.mention}** vs **{rakip.mention}**\n\n"
            f"Her tur her ikisi de aynı anda eylemini seçer.\n"
            f"**Kılıç**: güvenli hasar (Kalkan bloklar)\n"
            f"**Büyü**: güçlü ama ıskayabilir (Kalkanı deler)\n"
            f"**Kalkan**: Kılıcı tamamen, Büyüyü %55 azaltır"
        )
        await interaction.response.send_message(embed=e, view=view)
        view.msg = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(Arena(bot))
