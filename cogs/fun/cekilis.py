"""
cogs/fun/cekilis.py — /çekiliş: Süreli, katılım butonlu çekiliş.
"""
from __future__ import annotations
import asyncio
import random
import discord
from discord import app_commands
from discord.ext import commands
from .._v2 import (
    c_text, c_section, c_thumbnail, c_separator, c_container,
    respond, msg_edit,
)


class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.participants: set[int] = set()

    @discord.ui.button(label="Katıl", emoji="🎉", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, _: discord.ui.Button):
        uid = interaction.user.id
        if uid in self.participants:
            self.participants.discard(uid)
            await interaction.response.send_message("❌ Çekilişten ayrıldın.", ephemeral=True)
        else:
            self.participants.add(uid)
            await interaction.response.send_message("✅ Çekilişe katıldın!", ephemeral=True)


def _build_card(
    prize: str,
    host: discord.Member,
    ends_ts: int,
    winner_count: int,
    participant_count: int,
    *,
    finished: bool = False,
    winners: list[str] | None = None,
) -> discord.ui.Container:
    if finished:
        if winners:
            title = "## 🎊 Çekiliş Bitti!"
            body  = (
                f"**Ödül:** {prize}\n"
                f"**Kazananlar:** {', '.join(winners)}\n"
                f"-# {participant_count} katılımcı arasından seçildi."
            )
        else:
            title = "## 😔 Çekiliş Bitti"
            body  = f"**Ödül:** {prize}\n-# Kimse katılmadı."
    else:
        title = "## 🎉 Çekiliş!"
        body  = (
            f"**Ödül:** {prize}\n"
            f"**Bitiş:** <t:{ends_ts}:R>\n"
            f"**Kazanan Sayısı:** {winner_count}\n"
            f"**Katılımcı:** {participant_count}"
        )

    return c_container(
        c_section(
            c_text(title),
            c_text(f"-# Düzenleyen: {host.display_name}"),
            accessory=c_thumbnail(str(host.display_avatar.url)),
        ),
        c_separator(),
        c_text(body),
    )


async def _end_giveaway(
    msg: discord.Message,
    view: GiveawayView,
    prize: str,
    host: discord.Member,
    ends_ts: int,
    winner_count: int,
    delay: float,
    guild: discord.Guild,
    channel: discord.abc.Messageable,
) -> None:
    await asyncio.sleep(delay)

    pool = list(view.participants)
    random.shuffle(pool)
    view.stop()

    winners: list[str] = []
    for uid in pool[:winner_count]:
        member = guild.get_member(uid)
        if member:
            winners.append(member.mention)

    final_card = _build_card(
        prize, host, ends_ts, winner_count, len(pool),
        finished=True, winners=winners,
    )
    try:
        await msg_edit(msg, final_card)
    except discord.HTTPException:
        pass

    if winners and hasattr(channel, "send"):
        winner_text = ", ".join(winners)
        try:
            await channel.send(  # type: ignore[union-attr]
                f"🎊 Tebrikler {winner_text}! **{prize}** kazandınız! 🎉"
            )
        except discord.HTTPException:
            pass


class Giveaway(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="çekiliş", description="Çekiliş başlatır.")
    @app_commands.describe(
        ödül="Çekiliş ödülü",
        süre="Süre (dakika, max 7 gün)",
        kazanan_sayısı="Kazanan sayısı (varsayılan 1)",
    )
    @app_commands.guild_only()
    async def cekilis(
        self,
        interaction: discord.Interaction,
        ödül: str,
        süre: app_commands.Range[int, 1, 10080],
        kazanan_sayısı: app_commands.Range[int, 1, 20] = 1,
    ) -> None:
        host     = interaction.user  # type: ignore[assignment]
        ends_ts  = int(discord.utils.utcnow().timestamp() + süre * 60)
        view     = GiveawayView()
        card     = _build_card(ödül, host, ends_ts, kazanan_sayısı, 0)
        msg      = await respond(interaction, card, view=view)

        if msg is None:
            return

        asyncio.create_task(
            _end_giveaway(
                msg,        # type: ignore[arg-type]
                view,
                ödül,
                host,
                ends_ts,
                kazanan_sayısı,
                süre * 60.0,
                interaction.guild,  # type: ignore[arg-type]
                interaction.channel,  # type: ignore[arg-type]
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
