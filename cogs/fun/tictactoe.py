"""
cogs/fun/tictactoe.py — Tic-Tac-Toe (/xox)
Bot veya insan rakibe karşı, sıra tabanlı XOX oyunu.
"""
from __future__ import annotations
import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import (
    c_text, c_section, c_thumbnail, c_separator, c_container, c_card,
    update, msg_edit, channel_send, respond,
)

X = "X"
O = "O"

_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]


# ── Oyun Motoru ───────────────────────────────────────────────────────────────

def _check_winner(board: list[str | None]) -> str | None:
    for a, b, c in _LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def _minimax(board: list[str | None], is_bot: bool) -> int:
    w = _check_winner(board)
    if w == O:
        return 1
    if w == X:
        return -1
    if None not in board:
        return 0
    scores = []
    for i in range(9):
        if board[i] is None:
            board[i] = O if is_bot else X
            scores.append(_minimax(board, not is_bot))
            board[i] = None
    return max(scores) if is_bot else min(scores)


def _best_move(board: list[str | None]) -> int:
    best   = -2
    best_i = next(i for i in range(9) if board[i] is None)
    for i in range(9):
        if board[i] is None:
            board[i] = O
            s = _minimax(board, False)
            board[i] = None
            if s > best:
                best, best_i = s, i
    return best_i


class TTTGame:
    def __init__(
        self,
        player_x: discord.Member,
        player_o: discord.Member | None = None,
        *,
        vs_bot: bool = False,
    ):
        self.board: list[str | None] = [None] * 9
        self.player_x = player_x
        self.player_o = player_o   # None → bot
        self.vs_bot   = vs_bot
        self.current  = X
        self.winner: str | None = None  # "X" | "O" | "draw"
        self.finished = False

    def place(self, pos: int, symbol: str) -> bool:
        if self.board[pos] is not None or self.finished:
            return False
        self.board[pos] = symbol
        w = _check_winner(self.board)
        if w:
            self.winner, self.finished = w, True
        elif None not in self.board:
            self.winner, self.finished = "draw", True
        else:
            self.current = O if symbol == X else X
        return True


# ── Hücre Butonu ─────────────────────────────────────────────────────────────

class CellButton(discord.ui.Button["TTTView"]):
    def __init__(self, pos: int, cell: str | None, disabled: bool):
        if cell == X:
            style, emoji = discord.ButtonStyle.danger,   "❌"
        elif cell == O:
            style, emoji = discord.ButtonStyle.primary,  "⭕"
        else:
            style, emoji = discord.ButtonStyle.secondary, "⬜"
        super().__init__(style=style, emoji=emoji, row=pos // 3, disabled=disabled)
        self.pos = pos

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.handle_move(interaction, self.pos)


# ── Oyun View ─────────────────────────────────────────────────────────────────

class TTTView(discord.ui.View):
    def __init__(self, game: TTTGame):
        super().__init__(timeout=300)
        self.game = game
        self.msg: discord.Message | None = None
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        self.clear_items()
        g = self.game
        for i in range(9):
            disabled = (g.board[i] is not None) or g.finished
            self.add_item(CellButton(i, g.board[i], disabled))

    def build_card(self, note: str = "") -> discord.ui.Container:
        g      = self.game
        o_name = g.player_o.display_name if g.player_o else "🤖 Bot"

        if g.finished:
            if g.winner == "draw":
                title = "## 🤝 Berabere!"
                sub   = f"❌ {g.player_x.display_name}  vs  ⭕ {o_name}"
            elif g.winner == X:
                title = f"## 🏆 {g.player_x.display_name} Kazandı!"
                sub   = "❌ birinci oldu"
            else:
                title = f"## 🏆 {o_name} Kazandı!"
                sub   = "⭕ birinci oldu"
            avatar = str(g.player_x.display_avatar.url)
        else:
            sym      = "❌" if g.current == X else "⭕"
            cur_name = g.player_x.display_name if g.current == X else o_name
            title    = "## ❌⭕ XOX"
            sub      = f"Sıra: {sym} **{cur_name}**"
            cur_m    = g.player_x if g.current == X else g.player_o
            avatar   = str(cur_m.display_avatar.url) if cur_m else str(g.player_x.display_avatar.url)

        items: list[discord.ui.Item] = [
            c_section(
                c_text(
                    f"{title}\n"
                    f"-# {sub}\n"
                    f"-# ❌ {g.player_x.display_name}  vs  ⭕ {o_name}"
                ),
                accessory=c_thumbnail(avatar),
            ),
        ]
        if note:
            items.append(c_separator())
            items.append(c_text(f"-# {note}"))

        return c_container(*items)

    async def handle_move(self, interaction: discord.Interaction, pos: int) -> None:
        g = self.game

        # Sıra ve sahiplik kontrolü
        if g.vs_bot:
            if interaction.user.id != g.player_x.id:
                await interaction.response.send_message("⛔ Bu oyun sana ait değil!", ephemeral=True)
                return
        else:
            expected = g.player_x if g.current == X else g.player_o
            if interaction.user.id != expected.id:
                await interaction.response.send_message("⛔ Şu an sıra sende değil!", ephemeral=True)
                return

        if not g.place(pos, g.current):
            await interaction.response.send_message("⛔ Bu kare dolu!", ephemeral=True)
            return

        self._sync_buttons()

        # Oyun bitti mi?
        if g.finished:
            card    = self.build_card()
            rematch = TTTRematchView(g, card)
            await update(interaction, card, view=rematch)
            if self.msg:
                rematch.msg = self.msg
            self.stop()
            return

        # Bot hamlesi
        if g.vs_bot:
            for btn in self.children:
                btn.disabled = True
            await update(interaction, self.build_card("🤖 Bot düşünüyor..."), view=self)

            await asyncio.sleep(0.7)
            if self.is_finished():
                return

            g.place(_best_move(g.board), O)
            self._sync_buttons()

            card = self.build_card()
            assert self.msg
            if g.finished:
                rematch = TTTRematchView(g, card)
                await msg_edit(self.msg, card, view=rematch)
                rematch.msg = self.msg
                self.stop()
            else:
                await msg_edit(self.msg, card, view=self)
        else:
            await update(interaction, self.build_card(), view=self)

    async def on_timeout(self) -> None:
        for btn in self.children:
            btn.disabled = True
        if self.msg:
            try:
                await msg_edit(self.msg, self.build_card("⏰ Oyun süresi doldu."), view=self)
            except discord.HTTPException:
                pass


# ── Tekrar Oyna View ──────────────────────────────────────────────────────────

class TTTRematchView(discord.ui.View):
    def __init__(self, game: TTTGame, son_kart: discord.ui.Container):
        super().__init__(timeout=120)
        self.game     = game
        self.son_kart = son_kart
        self.msg: discord.Message | None = None

    async def on_timeout(self) -> None:
        for btn in self.children:
            btn.disabled = True
        if self.msg:
            try:
                await msg_edit(self.msg, self.son_kart, view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Tekrar Oyna", emoji="🔄", style=discord.ButtonStyle.success)
    async def rematch(self, interaction: discord.Interaction, btn: discord.ui.Button) -> None:
        g = self.game
        allowed = {g.player_x.id}
        if g.player_o:
            allowed.add(g.player_o.id)
        if interaction.user.id not in allowed:
            await interaction.response.send_message("Bu oyuna dahil değildin!", ephemeral=True)
            return

        btn.disabled = True
        self.stop()
        await update(interaction, self.son_kart, view=self)

        new_game      = TTTGame(g.player_x, g.player_o, vs_bot=g.vs_bot)
        new_view      = TTTView(new_game)
        msg           = await channel_send(interaction.channel, new_view.build_card(), view=new_view)
        new_view.msg  = msg


# ── Davet View (PvP) ──────────────────────────────────────────────────────────

class TTTChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent   = opponent
        self.message: discord.Message | None = None

    async def on_timeout(self) -> None:
        for btn in self.children:
            btn.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⏰ Davet süresi doldu.", view=self)
            except discord.HTTPException:
                pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Bu davet sana değil!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Kabul Et", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"✅ **{self.opponent.display_name}** kabul etti! Oyun başlıyor...",
            view=self,
        )
        self.stop()

        game     = TTTGame(self.challenger, self.opponent, vs_bot=False)
        view     = TTTView(game)
        msg      = await channel_send(interaction.channel, view.build_card(), view=view)
        view.msg = msg

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"❌ **{self.opponent.display_name}** daveti reddetti.",
            view=self,
        )
        self.stop()


# ── Cog ───────────────────────────────────────────────────────────────────────

class TicTacToe(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="xox", description="XOX (Tic-Tac-Toe) oyna. Bot veya rakip seç.")
    @app_commands.describe(rakip="Rakip kişi (boş bırakırsan bota karşı oynarsın)")
    @app_commands.guild_only()
    async def xox(self, interaction: discord.Interaction, rakip: discord.Member | None = None) -> None:
        if rakip is None:
            game     = TTTGame(interaction.user, vs_bot=True)
            view     = TTTView(game)
            msg      = await respond(interaction, view.build_card(), view=view)
            view.msg = msg
            return

        if rakip.id == interaction.user.id:
            await respond(
                interaction,
                c_card("## ❌ Hata", body="Kendinle oynayamazsın!"),
                ephemeral=True,
            )
            return

        if rakip.bot:
            await respond(
                interaction,
                c_card("## ❌ Hata", body="Botlarla oynayamazsın! `/xox` yazarak bota karşı oynayabilirsin."),
                ephemeral=True,
            )
            return

        view = TTTChallengeView(interaction.user, rakip)
        await interaction.response.send_message(
            content=f"🎯 {rakip.mention}, **{interaction.user.display_name}** seni XOX oyununa davet ediyor!",
            view=view,
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicTacToe(bot))
