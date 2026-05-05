import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from ._shared import fun_embed, giphy
from .._v2 import (
    c_text, c_thumbnail, c_section, c_container, c_separator, c_media,
    respond, update, channel_send, msg_edit,
)

MAX_OYUNCU = 6
LOBI_SURE  = 60
TETIK_SURE = 45


def _ihtimal_bar(kalan_oda: int) -> str:
    toplam = 6
    ateşlendi = toplam - kalan_oda
    return "🟡" * kalan_oda + "⬛" * ateşlendi


class RusRuletiOyun:
    def __init__(self, oyuncular: list[discord.Member]):
        self.oyuncular  = list(oyuncular)
        self.kalan_oda  = 6
        self.mevcut_idx = 0

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
        self.başlatan  = başlatan
        self.oyuncular = [başlatan]
        self.msg: discord.Message | None = None
        self.started   = False

    def _card(self) -> tuple[dict, ...]:
        lines = (
            ["**🔫 Rus Ruleti — Lobi**", "", f"**{len(self.oyuncular)}/{MAX_OYUNCU}** oyuncu", ""]
            + [f"• {o.mention}" for o in self.oyuncular]
            + ["", "-# Katılmak için **Katıl** butonuna bas."]
        )
        return (c_container(c_text("\n".join(lines)), color=0xED4245),)

    @discord.ui.button(label="Katıl", emoji="✋", style=discord.ButtonStyle.success)
    async def katıl(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user in self.oyuncular:
            return await interaction.response.send_message("Zaten lobidesin!", ephemeral=True)
        if len(self.oyuncular) >= MAX_OYUNCU:
            return await interaction.response.send_message("Lobi dolu!", ephemeral=True)
        self.oyuncular.append(interaction.user)
        if len(self.oyuncular) >= MAX_OYUNCU:
            btn.disabled = True
        await update(interaction, *self._card(), view=self)

    @discord.ui.button(label="Ayrıl", emoji="🚪", style=discord.ButtonStyle.secondary)
    async def ayrıl(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyuncular:
            return await interaction.response.send_message("Lobide değilsin!", ephemeral=True)
        if interaction.user == self.başlatan:
            return await interaction.response.send_message(
                "Kurucu ayrılamaz. Lobi kapatmak için **İptal** butonunu kullan.", ephemeral=True
            )
        self.oyuncular.remove(interaction.user)
        for c in self.children:
            if hasattr(c, "label") and c.label == "Katıl":
                c.disabled = False
        await update(interaction, *self._card(), view=self)

    @discord.ui.button(label="Başlat", emoji="▶️", style=discord.ButtonStyle.primary)
    async def başlat(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user.id != self.başlatan.id:
            return await interaction.response.send_message("Sadece başlatan başlatabilir.", ephemeral=True)
        if len(self.oyuncular) < 2:
            return await interaction.response.send_message("En az 2 oyuncu gerekli!", ephemeral=True)
        self.started = True
        for c in self.children:
            c.disabled = True
        await update(interaction,
            c_container(c_text("**🔫 Rus Ruleti**\n\nOyun başlıyor..."), color=0xED4245),
            view=self,
        )
        self.stop()
        await _oyunu_başlat(interaction, self.oyuncular)

    @discord.ui.button(label="İptal", emoji="✖️", style=discord.ButtonStyle.danger)
    async def iptal(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user.id != self.başlatan.id:
            return await interaction.response.send_message("Sadece başlatan iptal edebilir.", ephemeral=True)
        self.started = True
        self.stop()
        for c in self.children:
            c.disabled = True
        await update(interaction,
            c_container(
                c_text(f"**🚫 Lobi İptal Edildi**\n\n{interaction.user.mention} lobi iptal etti."),
                color=0x95A5A6,
            ),
            view=self,
        )

    async def on_timeout(self):
        if self.started:
            return
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await msg_edit(self.msg,
                    c_container(c_text("**🔫 Rus Ruleti**\n\n⏰ Lobi süresi doldu."), color=0x95A5A6),
                    view=self,
                )
            except discord.HTTPException:
                pass


# ── Oyun Görünümü ─────────────────────────────────────────────────────────────

class TetikView(discord.ui.View):
    def __init__(self, oyun: RusRuletiOyun, kanal: discord.abc.Messageable):
        super().__init__(timeout=TETIK_SURE)
        self.oyun        = oyun
        self.kanal       = kanal
        self.msg: discord.Message | None = None
        self._tamamlandı = False

    def _card(self, sonuç_metni: str = "") -> dict:
        oyun    = self.oyun
        oyuncu  = oyun.mevcut_oyuncu
        ihtimal = round(100 / oyun.kalan_oda) if oyun.kalan_oda > 0 else 100
        lines = [
            "**🔫 Rus Ruleti**",
            "",
            f"**Sıra:** {oyuncu.mention}",
            "",
            _ihtimal_bar(oyun.kalan_oda),
            f"**Kalan oda:** {oyun.kalan_oda} / 6  •  **Ölüm ihtimali:** %{ihtimal}",
            "",
            "**Oyuncular:**",
        ] + [o.mention for o in oyun.oyuncular]
        if sonuç_metni:
            lines += ["", sonuç_metni]
        return c_container(
            c_section(
                c_text("\n".join(lines)),
                accessory=c_thumbnail(str(oyuncu.display_avatar.url)),
            ),
            color=0xED4245,
        )

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
            for c in self.children:
                c.disabled = True
            await update(interaction,
                c_container(
                    c_section(
                        c_text(
                            f"**💀 Bang!**\n\n"
                            f"{kurban.mention} tetiği çekti ve **hayatını kaybetti!** 💥\n\n"
                            f"%{round(ihtimal * 100)} ihtimale rağmen..."
                        ),
                        accessory=c_thumbnail(str(kurban.display_avatar.url)),
                    ),
                    color=0xED4245,
                ),
                view=self,
            )
            await asyncio.sleep(2)
            await _oyun_bitti(interaction, self.oyun, kurban)
        else:
            await update(interaction,
                c_container(
                    c_text(
                        f"**😮‍💨 Click...**\n\n"
                        f"{interaction.user.mention} tetiği çekti — **boş!** Nefes aldın.\n\n"
                        f"{_ihtimal_bar(self.oyun.kalan_oda)}\n"
                        f"**Kalan oda:** {self.oyun.kalan_oda} / 6"
                    ),
                    color=0xF0A030,
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
                await msg_edit(self.msg,
                    c_container(
                        c_text(
                            f"**⏰ Süre Doldu**\n\n"
                            f"{oyuncu.mention} süresi içinde tetiği çekmedi — korktu mu? 🐔\n"
                            f"Oyun sona erdi."
                        ),
                        color=0x95A5A6,
                    ),
                    view=self,
                )
            except discord.HTTPException:
                pass


class TekrarOynaView(discord.ui.View):
    def __init__(self, oyuncular: list[discord.Member], başlatan: discord.Member, son_kart: tuple[dict, ...]):
        super().__init__(timeout=60)
        self.oyuncular = oyuncular
        self.başlatan  = başlatan
        self.son_kart  = son_kart
        self.msg: discord.Message | None = None

    @discord.ui.button(label="Tekrar Oyna", emoji="🔄", style=discord.ButtonStyle.success)
    async def tekrar(self, interaction: discord.Interaction, btn: discord.ui.Button):
        if interaction.user not in self.oyuncular:
            return await interaction.response.send_message("Oyuna dahil değildin!", ephemeral=True)
        btn.disabled = True
        self.stop()
        await update(interaction, *self.son_kart, view=self)
        lobi = LobiView(interaction.user)
        new_msg = await channel_send(interaction.channel, *lobi._card(), view=lobi)
        lobi.msg = new_msg

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.msg:
            try:
                await msg_edit(self.msg, *self.son_kart, view=self)
            except discord.HTTPException:
                pass


# ── Oyun Akışı ────────────────────────────────────────────────────────────────

async def _oyunu_başlat(interaction: discord.Interaction, oyuncular: list[discord.Member]):
    random.shuffle(oyuncular)
    oyun    = RusRuletiOyun(oyuncular)
    view    = TetikView(oyun, interaction.channel)
    sıra    = oyun.mevcut_oyuncu
    ihtimal = round(100 / oyun.kalan_oda)

    card = c_container(
        c_section(
            c_text(
                f"**🔫 Rus Ruleti — Başladı!**\n\n"
                f"**{len(oyuncular)}** oyuncu tabancayı paylaşıyor.\n"
                f"Silahda **1 mermi**, **6 oda**.\n\n"
                f"**İlk sıra:** {sıra.mention}\n\n"
                f"{_ihtimal_bar(oyun.kalan_oda)}\n"
                f"**Ölüm ihtimali:** %{ihtimal}"
            ),
            accessory=c_thumbnail(str(sıra.display_avatar.url)),
        ),
        color=0xED4245,
    )
    msg = await channel_send(interaction.channel, card, view=view)
    view.msg = msg


async def _sonraki_tur(interaction: discord.Interaction, oyun: RusRuletiOyun):
    sıra    = oyun.mevcut_oyuncu
    ihtimal = round(100 / oyun.kalan_oda) if oyun.kalan_oda > 0 else 100

    card = c_container(
        c_section(
            c_text(
                f"**🔫 Rus Ruleti**\n\n"
                f"**Sıra:** {sıra.mention}\n\n"
                f"{_ihtimal_bar(oyun.kalan_oda)}\n"
                f"**Kalan oda:** {oyun.kalan_oda} / 6  •  **Ölüm ihtimali:** %{ihtimal}\n\n"
                f"**Oyuncular:**\n" + "\n".join(o.mention for o in oyun.oyuncular)
            ),
            accessory=c_thumbnail(str(sıra.display_avatar.url)),
        ),
        color=0xED4245,
    )
    view = TetikView(oyun, interaction.channel)
    msg  = await channel_send(interaction.channel, card, view=view)
    view.msg = msg


async def _oyun_bitti(interaction: discord.Interaction, oyun: RusRuletiOyun, kurban: discord.Member):
    hayatta = [o for o in oyun.oyuncular if o.id != kurban.id]
    gif = await giphy("bang gunshot dead")

    hayatta_str = (
        "\n".join(f"🎉 {o.mention}" for o in hayatta) if hayatta else "_Kimse kalmadı._"
    )
    items = [
        c_section(
            c_text(
                f"**💀 Oyun Bitti**\n\n"
                f"**{kurban.mention}** hayatını kaybetti!\n\n"
                f"**Hayatta kalanlar:**\n{hayatta_str}"
            ),
            accessory=c_thumbnail(str(kurban.display_avatar.url)),
        ),
    ]
    if gif:
        items.append(c_separator())
        items.append(c_media(gif))

    son_kart = (c_container(*items, color=0xED4245),)
    view = TekrarOynaView(oyun.oyuncular, kurban, son_kart)
    msg  = await channel_send(interaction.channel, *son_kart, view=view)
    view.msg = msg


# ── Cog ───────────────────────────────────────────────────────────────────────

class RusRuleti(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rusruleti", description="Rus Ruleti oyna! 6 oda, 1 mermi.")
    async def rusruleti(self, interaction: discord.Interaction):
        lobi = LobiView(interaction.user)
        lobi.msg = await respond(interaction, *lobi._card(), view=lobi)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(
            embed=fun_embed("❌ Hata", str(error), discord.Color.red()),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(RusRuleti(bot))
