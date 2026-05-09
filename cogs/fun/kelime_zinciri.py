"""
cogs/fun/kelime_zinciri.py — /kelime: Kanal tabanlı kelime zinciri oyunu.
"""
from __future__ import annotations
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from .._v2 import c_text, c_section, c_separator, c_container, respond, channel_send

_TIMEOUT_SEC = 300  # 5 dakika

_TURKISH = set("abcçdefgğhıijklmnoöprsştuüvyz")


def _normalize(word: str) -> str:
    return word.casefold().replace("i̇", "i")


def _is_valid_word(word: str) -> bool:
    return len(word) >= 2 and all(c in _TURKISH for c in _normalize(word))


class GameState:
    def __init__(self, channel_id: int, starter_id: int):
        self.channel_id   = channel_id
        self.starter_id   = starter_id
        self.last_word:   str | None = None
        self.used_words:  set[str]   = set()
        self.last_player: int | None = None
        self._timeout_task: asyncio.Task | None = None

    @property
    def expected_letter(self) -> str | None:
        return _normalize(self.last_word)[-1] if self.last_word else None

    def reset_timeout(self, coro) -> None:
        if self._timeout_task:
            self._timeout_task.cancel()
        self._timeout_task = asyncio.create_task(coro)

    def stop(self) -> None:
        if self._timeout_task:
            self._timeout_task.cancel()
            self._timeout_task = None


_games: dict[int, GameState] = {}


class KelimeZinciri(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    kelime = app_commands.Group(name="kelime", description="Kelime zinciri oyunu")

    @kelime.command(name="başlat", description="Bu kanalda kelime zinciri oyununu başlatır.")
    @app_commands.guild_only()
    async def baslat(self, interaction: discord.Interaction) -> None:
        ch_id = interaction.channel_id
        if ch_id in _games:
            await respond(
                interaction,
                c_container(
                    c_text("## ⚠️ Oyun Zaten Aktif"),
                    c_separator(),
                    c_text("Bu kanalda zaten bir kelime zinciri oyunu var.\n`/kelime bitir` ile mevcut oyunu bitir."),
                ),
                ephemeral=True,
            )
            return

        state = GameState(ch_id, interaction.user.id)  # type: ignore[arg-type]
        _games[ch_id] = state  # type: ignore[index]
        state.reset_timeout(self._timeout(ch_id))  # type: ignore[arg-type]

        await respond(
            interaction,
            c_container(
                c_section(
                    c_text("## 🔡 Kelime Zinciri Başladı!"),
                    c_text(f"-# Başlatan: {interaction.user.display_name}"),
                ),
                c_separator(),
                c_text(
                    "**Nasıl oynanır?**\n"
                    "• Her kelime, bir öncekinin **son harfiyle** başlamalı.\n"
                    "• Aynı kelime iki kez kullanılamaz.\n"
                    "• En az **2 harf** içermeli, sadece Türkçe karakterler.\n\n"
                    "İlk kelimeyi yaz ve zinciri başlat!"
                ),
                c_separator(),
                c_text(f"-# {_TIMEOUT_SEC // 60} dakika sessizlik olursa oyun biter."),
            ),
        )

    @kelime.command(name="bitir", description="Bu kanaldaki kelime zinciri oyununu bitirir.")
    @app_commands.guild_only()
    async def bitir(self, interaction: discord.Interaction) -> None:
        ch_id = interaction.channel_id
        state = _games.get(ch_id)  # type: ignore[arg-type]
        if not state:
            await respond(
                interaction,
                c_container(c_text("## ❌ Aktif Oyun Yok"), c_separator(), c_text("Bu kanalda aktif oyun yok.")),
                ephemeral=True,
            )
            return

        if (
            interaction.user.id != state.starter_id
            and not interaction.user.guild_permissions.manage_messages  # type: ignore[union-attr]
        ):
            await respond(
                interaction,
                c_container(c_text("## ⛔ Yetki Yok"), c_separator(), c_text("Oyunu sadece başlatan kişi veya moderatörler bitirebilir.")),
                ephemeral=True,
            )
            return

        state.stop()
        del _games[ch_id]  # type: ignore[arg-type]

        word_count = len(state.used_words)
        await respond(
            interaction,
            c_container(
                c_text("## 🏁 Oyun Bitti!"),
                c_separator(),
                c_text(
                    f"Kelime zinciri sona erdi.\n"
                    f"**Toplam kelime:** {word_count}\n"
                    f"**Son kelime:** {state.last_word or '_Hiç kelime girilmedi_'}"
                ),
            ),
        )

    async def _timeout(self, ch_id: int) -> None:
        await asyncio.sleep(_TIMEOUT_SEC)
        state = _games.pop(ch_id, None)
        if state is None:
            return
        ch = self.bot.get_channel(ch_id)
        if ch and hasattr(ch, "send"):
            try:
                await channel_send(
                    ch,  # type: ignore[arg-type]
                    c_container(
                        c_text("## ⏰ Kelime Zinciri Zaman Aşımı"),
                        c_separator(),
                        c_text(
                            f"5 dakika boyunca kelime girilmedi, oyun bitti!\n"
                            f"**Toplam kelime:** {len(state.used_words)}\n"
                            f"**Son kelime:** {state.last_word or '_Hiç kelime girilmedi_'}"
                        ),
                    ),
                )
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return

        state = _games.get(message.channel.id)
        if state is None:
            return

        word = message.content.strip()

        # Ignore multi-word messages and commands
        if " " in word or word.startswith("/") or not word:
            return

        norm = _normalize(word)

        # Validate Turkish characters
        if not _is_valid_word(word):
            try:
                await message.reply("❌ Geçersiz kelime! Sadece Türkçe karakterler kullanabilirsin ve en az 2 harf olmalı.")
            except discord.HTTPException:
                pass
            return

        # Same player twice in a row (only with 2+ players)
        if state.last_player == message.author.id and len(state.used_words) > 0:
            try:
                await message.reply("❌ Arka arkaya oynayamazsın, başka birinin sırası!")
            except discord.HTTPException:
                pass
            return

        # Repeated word
        if norm in state.used_words:
            try:
                await message.reply(f"❌ **{word}** daha önce kullanıldı!")
            except discord.HTTPException:
                pass
            return

        # Check first letter
        expected = state.expected_letter
        if expected and _normalize(word)[0] != expected:
            try:
                await message.reply(
                    f"❌ Kelime **'{expected.upper()}'** harfiyle başlamalı! (Son kelime: **{state.last_word}**)"
                )
            except discord.HTTPException:
                pass
            return

        # Valid word
        state.used_words.add(norm)
        state.last_word   = word
        state.last_player = message.author.id
        state.reset_timeout(self._timeout(message.channel.id))

        next_letter = _normalize(word)[-1].upper()
        try:
            await message.reply(
                f"✅ **{word}** — {len(state.used_words)}. kelime! Sıradaki harf: **{next_letter}**"
            )
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(KelimeZinciri(bot))
