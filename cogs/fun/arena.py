import io
import asyncio

import discord
import aiohttp
from discord import app_commands
from discord.ext import commands
import random

from ._shared import giphy
from ._render import render_arena

# ── Sabitler ────────────────────────────────────────────────────────────────────

_EYLEM_EMOJI = {"kılıç": "⚔️", "büyü": "🔮", "kalkan": "🛡️"}
_EYLEM_LABEL = {"kılıç": "Kılıç", "büyü": "Büyü", "kalkan": "Kalkan"}

MAKS_HP  = 150
MAKS_TUR = 20


# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────────

def _hasar(saldirgan: str, savunmaci: str) -> tuple[int, str]:
    if saldirgan == "kalkan":
        return 0, ""

    if saldirgan == "kılıç":
        if savunmaci == "kalkan":
            return 0, "Kalkan engelledi!"
        dmg = random.randint(20, 35)
        if random.random() < 0.15:
            dmg = int(dmg * 1.6)
            return dmg, f"Kritik Kilic! {dmg} hasar"
        return dmg, f"Kilic {dmg} hasar verdi"

    # büyü
    if random.random() > 0.80:
        return 0, "Buyu iskaladi!"
    dmg = random.randint(30, 45)
    if savunmaci == "kalkan":
        dmg = int(dmg * 0.45)
        return dmg, f"Kalkan buyuyu hafifletti -> {dmg} hasar"
    if random.random() < 0.12:
        dmg = int(dmg * 1.6)
        return dmg, f"Kritik Buyu! {dmg} hasar"
    return dmg, f"Buyu {dmg} hasar verdi"


async def _fetch_bytes(url: str) -> bytes | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=4)) as r:
                return await r.read() if r.status == 200 else None
    except Exception:
        return None


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
        await interaction.response.defer()
        view = ArenaView(self.p1, self.p2)
        f, e = await view._render()
        e.description = f"{self.p1.mention}  ⚔️  {self.p2.mention}\n\n⏳ Her iki oyuncu da eylemini seçsin."
        msg = await interaction.channel.send(file=f, embed=e, view=view)
        view.msg = msg


# ── Ana Oyun View ────────────────────────────────────────────────────────────────

class ArenaView(discord.ui.View):
    def __init__(self, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=90)
        self.oyuncular = [p1, p2]
        self.hp        = [MAKS_HP, MAKS_HP]
        self.seçimler: dict[int, str] = {}
        self.tur       = 1
        self.msg: discord.Message | None = None

    async def _render(self, son_log: str = "") -> tuple[discord.File, discord.Embed]:
        p1, p2 = self.oyuncular
        av1, av2 = await asyncio.gather(
            _fetch_bytes(str(p1.display_avatar.url)),
            _fetch_bytes(str(p2.display_avatar.url)),
        )
        data = render_arena(
            p1_name=p1.display_name, p1_hp=self.hp[0], p1_secti=p1.id in self.seçimler,
            p2_name=p2.display_name, p2_hp=self.hp[1], p2_secti=p2.id in self.seçimler,
            max_hp=MAKS_HP, tur=self.tur, maks_tur=MAKS_TUR,
            son_log=son_log, p1_avatar_bytes=av1, p2_avatar_bytes=av2,
        )
        f = discord.File(io.BytesIO(data), filename="arena.png")
        e = discord.Embed(color=discord.Color.from_rgb(180, 30, 30))
        e.set_image(url="attachment://arena.png")
        e.set_footer(text="⚔️ Kılıç: güvenli  •  🔮 Büyü: güçlü  •  🛡️ Kalkan: savunma")
        e.timestamp = discord.utils.utcnow()
        return f, e

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
        f, e = await self._render()
        await self.msg.edit(attachments=[f], embed=e)

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
        log_lines = [
            f"{p1n} -> {_EYLEM_LABEL[e1]}   |   {p2n} -> {_EYLEM_LABEL[e2]}",
        ]
        if acik2:
            log_lines.append(f"{p1n}: {acik2}")
        if acik1:
            log_lines.append(f"{p2n}: {acik1}")
        son_log = "\n".join(log_lines)

        self.tur += 1
        self.seçimler.clear()

        # ── Oyun bitti mi? ───────────────────────────────────────────────────
        bitti = self.hp[0] <= 0 or self.hp[1] <= 0 or self.tur > MAKS_TUR
        if bitti:
            self.stop()
            for c in self.children:
                c.disabled = True

            if self.hp[0] <= 0 and self.hp[1] <= 0:
                başlık, renk, tag = "🤝 Berabere! İkiniz de yıkıldınız.", discord.Color.greyple(), "tie draw"
            elif self.hp[0] <= 0:
                başlık, renk, tag = f"🏆 {p2n} kazandı!", discord.Color.green(), "victory winner"
            elif self.hp[1] <= 0:
                başlık, renk, tag = f"🏆 {p1n} kazandı!", discord.Color.green(), "victory winner"
            else:
                kazanan = p1n if self.hp[0] > self.hp[1] else p2n
                başlık, renk, tag = f"⏱️ {kazanan} daha fazla canla hayatta kaldı!", discord.Color.gold(), "victory winner"

            gif = await giphy(tag)
            embed = discord.Embed(title=başlık, color=renk)
            embed.add_field(name=p1n, value=f"{self.hp[0]} / {MAKS_HP} HP", inline=True)
            embed.add_field(name=p2n, value=f"{self.hp[1]} / {MAKS_HP} HP", inline=True)
            embed.add_field(name="📋 Son Eylem", value=son_log, inline=False)
            if gif:
                embed.set_image(url=gif)
            embed.timestamp = discord.utils.utcnow()
            tekrar = ArenaTekrarView(self.oyuncular[0], self.oyuncular[1])
            await self.msg.edit(attachments=[], embed=embed, view=tekrar)
            tekrar.msg = self.msg
            return

        f, e = await self._render(son_log)
        await self.msg.edit(attachments=[f], embed=e, view=self)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                e = discord.Embed(
                    title="⏰ Süre Doldu — Dövüş İptal!",
                    color=discord.Color.greyple(),
                    timestamp=discord.utils.utcnow(),
                )
                await self.msg.edit(attachments=[], embed=e, view=self)
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

        await interaction.response.defer()
        p1   = interaction.user
        view = ArenaView(p1, rakip)
        f, e = await view._render()
        e.description = f"{p1.mention}  ⚔️  {rakip.mention}\n\n⏳ Her iki oyuncu da eylemini seçsin."
        msg = await interaction.followup.send(file=f, embed=e, view=view)
        view.msg = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(Arena(bot))
