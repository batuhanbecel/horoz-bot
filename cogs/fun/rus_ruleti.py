import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from ._shared import fun_embed

MAX_OYUNCU = 6
LOBI_SURE  = 60   # seconds to wait for players
TETIK_SURE = 45   # seconds per turn


def _ihtimal_bar(kalan_oda: int) -> str:
    """Visual chamber indicator: 6 slots, filled = live bullet, empty = safe."""
    # kalan_oda: remaining safe chambers (oda sayısı - çekilenler)
    toplam = 6
    ateşlendi = toplam - kalan_oda
    # chambers: ■ = pulled (empty), 🟡 = remaining (unknown)
    return "🟡" * kalan_oda + "⬛" * ateşlendi


class RusRuletiOyun:
    def __init__(self, oyuncular: list[discord.Member]):
        self.oyuncular  = list(oyuncular)
        self.kalan_oda  = 6   # chambers not yet pulled
        self.mevcut_idx = 0   # whose turn it is (index into oyuncular)

    @property
    def mevcut_oyuncu(self) -> discord.Member:
        return self.oyuncular[self.mevcut_idx % len(self.oyuncular)]

    def tetik_cek(self) -> tuple[bool, float]:
        ihtimal = 1 / self.kalan_oda
        öldü    = random.random() < ihtimal
        self.kalan_oda -= 1
        if not öldü:
            self.mevcut_idx = (self.mevcut_idx + 1) % len(self.oyuncular)
        return öldü, ihtimal


# ── Lobi ──────────────────────────────────────────────────────────────────────

class LobiView(discord.ui.View):
    def __init__(self, başlatan: discord.Member):
        super().__init__(timeout=LOBI_SURE)
        self.başlatan   = başlatan
        self.oyuncular  = [başlatan]
        self.msg: discord.Message | None = None
        self.started    = False

    def _embed(self) -> discord.Embed:
        e = fun_embed(
            "🔫 Rus Ruleti — Lobi",
            f"**{len(self.oyuncular)}/{MAX_OYUNCU}** oyuncu\n\n"
            + "\n".join(f"• {o.mention}" for o in self.oyuncular)
            + "\n\n_Katılmak için **Katıl** butonuna bas._",
            discord.Color.dark_red(),
        )
        e.set_footer(text=f"Başlatan: {self.başlatan.display_name} • Horoz Bot")
        return e

    async def _güncelle(self, interaction: discord.Interaction | None = None):
        if interaction:
            await interaction.response.edit_message(embed=self._embed(), view=self)
        elif self.msg:
            await self.msg.edit(embed=self._embed(), view=self)

    @discord.ui.button(label="Katıl", emoji="🙋", style=discord.ButtonStyle.success)
    async def katıl(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user in self.oyuncular:
            return await interaction.response.send_message("Zaten lobidesin!", ephemeral=True)
        if len(self.oyuncular) >= MAX_OYUNCU:
            return await interaction.response.send_message("Lobi dolu!", ephemeral=True)
        self.oyuncular.append(interaction.user)
        if len(self.oyuncular) >= MAX_OYUNCU:
            btn.disabled = True
        await self._güncelle(interaction)

    @discord.ui.button(label="Ayrıl", emoji="🚪", style=discord.ButtonStyle.secondary)
    async def ayrıl(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyuncular:
            return await interaction.response.send_message("Lobide değilsin!", ephemeral=True)
        if interaction.user == self.başlatan:
            return await interaction.response.send_message("Başlatan ayrılamaz.", ephemeral=True)
        self.oyuncular.remove(interaction.user)
        # re-enable join button if it was disabled
        for c in self.children:
            if hasattr(c, "label") and c.label == "Katıl":
                c.disabled = False
        await self._güncelle(interaction)

    @discord.ui.button(label="Başlat", emoji="🎯", style=discord.ButtonStyle.danger)
    async def başlat(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user.id != self.başlatan.id:
            return await interaction.response.send_message("Sadece başlatan başlatabilir.", ephemeral=True)
        if len(self.oyuncular) < 2:
            return await interaction.response.send_message("En az 2 oyuncu gerekli!", ephemeral=True)
        self.started = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(
            embed=fun_embed("🔫 Rus Ruleti", "Oyun başlıyor...", discord.Color.dark_red()),
            view=self,
        )
        self.stop()
        await _oyunu_başlat(interaction, self.oyuncular)

    async def on_timeout(self):
        if self.started:
            return
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await self.msg.edit(
                    embed=fun_embed("🔫 Rus Ruleti", "⏰ Lobi süresi doldu.", discord.Color.greyple()),
                    view=self,
                )
            except discord.HTTPException:
                pass


# ── Oyun Görünümü ─────────────────────────────────────────────────────────────

class TetikView(discord.ui.View):
    def __init__(self, oyun: RusRuletiOyun, kanal: discord.TextChannel | discord.DMChannel):
        super().__init__(timeout=TETIK_SURE)
        self.oyun  = oyun
        self.kanal = kanal
        self.msg: discord.Message | None = None
        self._tamamlandı = False

    def _embed(self, sonuç_metni: str = "") -> discord.Embed:
        oyun  = self.oyun
        oyuncu = oyun.mevcut_oyuncu
        ihtimal = round(100 / oyun.kalan_oda) if oyun.kalan_oda > 0 else 100

        e = fun_embed(
            "🔫 Rus Ruleti",
            f"**Sıra:** {oyuncu.mention}\n\n"
            f"{_ihtimal_bar(oyun.kalan_oda)}\n"
            f"**Kalan oda:** {oyun.kalan_oda} / 6  •  **Ölüm ihtimali:** %{ihtimal}\n\n"
            + (f"**Oyuncular:**\n" + "\n".join(o.mention for o in oyun.oyuncular))
            + (f"\n\n{sonuç_metni}" if sonuç_metni else ""),
            discord.Color.dark_red(),
        )
        e.set_thumbnail(url=oyuncu.display_avatar.url)
        e.set_footer(text="Horoz Bot • Rus Ruleti")
        return e

    @discord.ui.button(label="Tetiği Çek", emoji="🔫", style=discord.ButtonStyle.danger)
    async def tetik(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user.id != self.oyun.mevcut_oyuncu.id:
            return await interaction.response.send_message(
                f"Sıra sende değil! Sıra: {self.oyun.mevcut_oyuncu.mention}", ephemeral=True
            )
        self._tamamlandı = True
        self.stop()

        öldü, ihtimal = self.oyun.tetik_cek()

        if öldü:
            kurban = interaction.user
            btn.disabled = True
            await interaction.response.edit_message(
                embed=fun_embed(
                    "💀 Bang!",
                    f"{kurban.mention} tetiği çekti ve **hayatını kaybetti!** 💥\n\n"
                    f"%{round(ihtimal * 100)} ihtimale rağmen...",
                    discord.Color.dark_red(),
                ),
                view=self,
            )
            await asyncio.sleep(2)
            await _oyun_bitti(interaction, self.oyun, kurban)
        else:
            await interaction.response.edit_message(
                embed=fun_embed(
                    "😮‍💨 Click...",
                    f"{interaction.user.mention} tetiği çekti — **boş!** Nefes aldın.\n\n"
                    f"{_ihtimal_bar(self.oyun.kalan_oda)}\n"
                    f"**Kalan oda:** {self.oyun.kalan_oda} / 6",
                    discord.Color.orange(),
                ),
                view=self,
            )
            await asyncio.sleep(1.5)
            await _sonraki_tur(interaction, self.oyun)

    async def on_timeout(self):
        if self._tamamlandı:
            return
        oyuncu = self.oyun.mevcut_oyuncu
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await self.msg.edit(
                    embed=fun_embed(
                        "⏰ Süre Doldu",
                        f"{oyuncu.mention} süresi içinde tetiği çekmedi — korktu mu? 🐔\n"
                        f"Oyun sona erdi.",
                        discord.Color.greyple(),
                    ),
                    view=self,
                )
            except discord.HTTPException:
                pass


class TekrarOynaView(discord.ui.View):
    def __init__(self, oyuncular: list[discord.Member], başlatan: discord.Member):
        super().__init__(timeout=60)
        self.oyuncular = oyuncular
        self.başlatan  = başlatan
        self.msg: discord.Message | None = None

    @discord.ui.button(label="Tekrar Oyna", emoji="🔄", style=discord.ButtonStyle.success)
    async def tekrar(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyuncular:
            return await interaction.response.send_message("Oyuna dahil değildin!", ephemeral=True)
        btn.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)
        lobi = LobiView(interaction.user)
        msg = await interaction.channel.send(embed=lobi._embed(), view=lobi)
        lobi.msg = msg

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await self.msg.edit(view=self)
            except discord.HTTPException:
                pass


# ── Oyun Akışı ────────────────────────────────────────────────────────────────

async def _oyunu_başlat(interaction: discord.Interaction, oyuncular: list[discord.Member]):
    random.shuffle(oyuncular)
    oyun   = RusRuletiOyun(oyuncular)
    view   = TetikView(oyun, interaction.channel)
    sıra   = oyun.mevcut_oyuncu
    ihtimal = round(100 / oyun.kalan_oda)

    e = fun_embed(
        "🔫 Rus Ruleti — Başladı!",
        f"**{len(oyuncular)}** oyuncu tabancayı paylaşıyor.\n"
        f"Silahda **1 mermi**, **6 oda**.\n\n"
        f"**İlk sıra:** {sıra.mention}\n\n"
        f"{_ihtimal_bar(oyun.kalan_oda)}\n"
        f"**Ölüm ihtimali:** %{ihtimal}",
        discord.Color.dark_red(),
    )
    e.set_footer(text="Horoz Bot • Rus Ruleti")
    msg = await interaction.channel.send(embed=e, view=view)
    view.msg = msg


async def _sonraki_tur(interaction: discord.Interaction, oyun: RusRuletiOyun):
    sıra    = oyun.mevcut_oyuncu
    ihtimal = round(100 / oyun.kalan_oda) if oyun.kalan_oda > 0 else 100

    e = fun_embed(
        "🔫 Rus Ruleti",
        f"**Sıra:** {sıra.mention}\n\n"
        f"{_ihtimal_bar(oyun.kalan_oda)}\n"
        f"**Kalan oda:** {oyun.kalan_oda} / 6  •  **Ölüm ihtimali:** %{ihtimal}\n\n"
        f"**Oyuncular:**\n" + "\n".join(o.mention for o in oyun.oyuncular),
        discord.Color.dark_red(),
    )
    e.set_thumbnail(url=sıra.display_avatar.url)
    e.set_footer(text="Horoz Bot • Rus Ruleti")

    view = TetikView(oyun, interaction.channel)
    msg  = await interaction.channel.send(embed=e, view=view)
    view.msg = msg


async def _oyun_bitti(interaction: discord.Interaction, oyun: RusRuletiOyun, kurban: discord.Member):
    hayatta = [o for o in oyun.oyuncular if o.id != kurban.id]

    e = fun_embed(
        "💀 Oyun Bitti",
        f"**{kurban.mention}** hayatını kaybetti!\n\n"
        + (
            "**Hayatta kalanlar:**\n" + "\n".join(f"🎉 {o.mention}" for o in hayatta)
            if hayatta else "_Kimse kalmadı._"
        ),
        discord.Color.dark_red(),
    )
    e.set_thumbnail(url=kurban.display_avatar.url)
    e.set_footer(text="Horoz Bot • Rus Ruleti")

    view = TekrarOynaView(oyun.oyuncular, kurban)
    msg  = await interaction.channel.send(embed=e, view=view)
    view.msg = msg


# ── Cog ───────────────────────────────────────────────────────────────────────

class RusRuleti(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rusruleti", description="Rus Ruleti oyna! 6 oda, 1 mermi.")
    async def rusruleti(self, interaction: discord.Interaction):
        lobi = LobiView(interaction.user)
        await interaction.response.send_message(embed=lobi._embed(), view=lobi)
        lobi.msg = await interaction.original_response()

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(
            embed=fun_embed("❌ Hata", str(error), discord.Color.red()),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(RusRuleti(bot))
