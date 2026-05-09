"""
cogs/fun/cekilis.py — /çekiliş: Süreli, katılım butonlu çekiliş.
"""
from __future__ import annotations
import asyncio
import random
import discord
from discord import app_commands
from discord.ext import commands
from .._v2 import c_text, c_separator, c_container, respond, msg_edit


class GiveawayView(discord.ui.View):
    def __init__(self, prize: str, host: discord.Member, ends_ts: int, winner_count: int):
        super().__init__(timeout=None)
        self.prize        = prize
        self.host         = host
        self.ends_ts      = ends_ts
        self.winner_count = winner_count
        self.participants: set[int] = set()
        self.msg: discord.Message | None = None

    def build_card(
        self,
        *,
        finished: bool = False,
        winners: list[str] | None = None,
    ) -> discord.ui.Container:
        count = len(self.participants)
        if finished:
            if winners:
                title = "## 🎊 Çekiliş Bitti!"
                body  = (
                    f"**Ödül:** {self.prize}\n"
                    f"**Kazananlar:** {', '.join(winners)}\n"
                    f"-# {count} katılımcı arasından seçildi."
                )
            else:
                title = "## 😔 Çekiliş Bitti"
                body  = f"**Ödül:** {self.prize}\n-# Kimse katılmadı."
        else:
            title = "## 🎉 Çekiliş!"
            body  = (
                f"**Ödül:** {self.prize}\n"
                f"**Bitiş:** <t:{self.ends_ts}:R>\n"
                f"**Kazanan Sayısı:** {self.winner_count}\n"
                f"**Katılımcı:** {count}"
            )

        return c_container(
            c_text(title),
            c_separator(),
            c_text(body),
            c_separator(),
            c_text(f"-# Düzenleyen: {self.host.display_name}"),
        )

    @discord.ui.button(label="Katıl / Ayrıl", emoji="🎉", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        uid = interaction.user.id
        if uid in self.participants:
            self.participants.discard(uid)
            status = "❌ Çekilişten ayrıldın."
        else:
            self.participants.add(uid)
            status = "✅ Çekilişe katıldın!"

        if self.msg:
            try:
                await msg_edit(self.msg, self.build_card())
            except discord.HTTPException:
                pass

        await interaction.response.send_message(status, ephemeral=True)


async def _end_giveaway(
    view: GiveawayView,
    delay: float,
    guild: discord.Guild,
    channel: discord.abc.Messageable,
) -> None:
    await asyncio.sleep(delay)

    pool = list(view.participants)
    random.shuffle(pool)
    view.stop()

    winners: list[str] = []
    for uid in pool[:view.winner_count]:
        member = guild.get_member(uid)
        if member:
            winners.append(member.mention)

    if view.msg:
        try:
            await msg_edit(view.msg, view.build_card(finished=True, winners=winners))
        except discord.HTTPException:
            pass

    if winners and hasattr(channel, "send"):
        try:
            await channel.send(  # type: ignore[union-attr]
                f"🎊 Tebrikler {', '.join(winners)}! **{view.prize}** kazandınız! 🎉"
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
        host    = interaction.user  # type: ignore[assignment]
        ends_ts = int(discord.utils.utcnow().timestamp() + süre * 60)
        view    = GiveawayView(ödül, host, ends_ts, kazanan_sayısı)
        msg     = await respond(interaction, view.build_card(), view=view)

        if msg is None:
            return

        view.msg = msg  # type: ignore[assignment]
        asyncio.create_task(
            _end_giveaway(
                view,
                süre * 60.0,
                interaction.guild,   # type: ignore[arg-type]
                interaction.channel, # type: ignore[arg-type]
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
