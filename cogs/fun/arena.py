import asyncio
import random
from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands


# ────────────────────────────────────────────────────────────────────────────────
#  ArenaGame — Oyun Durumu & Kurallar
# ────────────────────────────────────────────────────────────────────────────────

@dataclass
class Fighter:
    """Bir savaşçının anlık durumunu tutan veri yapısı."""
    member: discord.Member
    hp: int = 100
    max_hp: int = 100
    ep: int = 50
    max_ep: int = 50
    potions_left: int = 2
    shield_active: bool = False
    is_bot: bool = False


class ArenaGame:
    """
    Sıra tabanlı arena oyununun *saf* mantık katmanı.
    Discord veya UI ile doğrudan iletişimi yoktur — sadece durum yönetir.
    """

    def __init__(
        self,
        challenger: discord.Member,
        opponent: discord.Member,
        is_vs_bot: bool = False,
    ):
        self.challenger = Fighter(challenger)
        self.opponent = Fighter(opponent, is_bot=is_vs_bot)
        self.turn_index: int = 0          # 0 = meydan okuyan, 1 = rakip
        self.turn_count: int = 1
        self.log: list[str] = []
        self.finished: bool = False
        self.winner: Fighter | None = None

    # ── Yardımcı Özellikler ───────────────────────────────────────────────────

    @property
    def current(self) -> Fighter:
        """Sırası gelen savaşçıyı döndürür."""
        return self.challenger if self.turn_index == 0 else self.opponent

    @property
    def other(self) -> Fighter:
        """Sırası gelmeyen (rakip) savaşçıyı döndürür."""
        return self.opponent if self.turn_index == 0 else self.challenger

    def _next_turn(self) -> None:
        """Sırayı diğer oyuncuya geçirir ve tur sayacını artırır."""
        self.turn_index = 1 - self.turn_index
        self.turn_count += 1

    def _hp_bar(self, value: int, maximum: int, length: int = 10) -> str:
        """Metin tabanlı bir ilerleme çubuğu üretir (█/░)."""
        ratio = value / maximum if maximum > 0 else 0
        filled = max(0, min(length, int(ratio * length)))
        return f"{'█' * filled}{'░' * (length - filled)}"

    def _log(self, line: str) -> None:
        """Savaş günlüğüne bir satır ekler (son 8 satır tutulur)."""
        self.log.append(line)
        if len(self.log) > 8:
            self.log.pop(0)

    # ── Eylem: Kılıç (Temel Saldırı) ───────────────────────────────────────────

    def action_sword(self) -> str:
        """
        ⚔️ 10–18 hasar verir. %20 şansla kritik (×1.5).
        Enerji harcamaz, aksine +10 EP kazandırır.
        Rakip kalkan aktifse hasar %80 düşürülür + 5 yansıma.
        """
        attacker = self.current
        defender = self.other

        base_dmg = random.randint(10, 18)
        is_crit = random.random() < 0.20

        if is_crit:
            base_dmg = int(base_dmg * 1.5)
            msg = f"⚔️ **{attacker.member.display_name}**: **Kritik Vuruş!** Kılıç ile `{base_dmg}` hasar verdi"
        else:
            msg = f"⚔️ **{attacker.member.display_name}**: Kılıç ile `{base_dmg}` hasar verdi"

        # Kalkan kontrolü: savunma aktifse hasarı %80 azalt, yansıma uygula
        if defender.shield_active:
            reduced = max(1, int(base_dmg * 0.20))   # geçen hasar (en az 1)
            blocked = base_dmg - reduced
            msg += f" (🛡️ Kalkan `{blocked}` engelledi, `{reduced}` geçti)"
            base_dmg = reduced
            defender.shield_active = False
            # Diken yansıması — saldırgana 5 hasar
            attacker.hp = max(0, attacker.hp - 5)
            msg += " → 🗡️ Diken: `5` yansıma hasarı aldı!"

        defender.hp = max(0, defender.hp - base_dmg)
        attacker.ep = min(attacker.max_ep, attacker.ep + 10)
        self._log(msg)
        self._next_turn()
        return msg

    # ── Eylem: Büyü (Ağır Saldırı) ─────────────────────────────────────────────

    def action_spell(self) -> str | None:
        """
        🔮 25–40 hasar verir. Bedeli 20 EP.
        Yeterli enerji yoksa None döner (tur geçişi olmaz).
        Kalkan etkisi kılıç ile aynıdır.
        """
        attacker = self.current
        if attacker.ep < 20:
            return None

        attacker.ep -= 20
        base_dmg = random.randint(25, 40)
        msg = f"🔮 **{attacker.member.display_name}**: Büyü ile `{base_dmg}` hasar verdi"

        defender = self.other
        if defender.shield_active:
            reduced = max(1, int(base_dmg * 0.20))
            blocked = base_dmg - reduced
            msg += f" (🛡️ Kalkan `{blocked}` engelledi, `{reduced}` geçti)"
            base_dmg = reduced
            defender.shield_active = False
            attacker.hp = max(0, attacker.hp - 5)
            msg += " → 🗡️ Diken: `5` yansıma hasarı aldı!"

        defender.hp = max(0, defender.hp - base_dmg)
        self._log(msg)
        self._next_turn()
        return msg

    # ── Eylem: Kalkan (Savunma + Yansıtma) ─────────────────────────────────────

    def action_shield(self) -> str | None:
        """
        🛡️ 10 EP harcar. Sonraki gelen saldırıyı %80 zayıflatır.
        Diken: saldırgana 5 sabit yansıma hasarı verir.
        Yeterli EP yoksa None döner.
        """
        attacker = self.current
        if attacker.ep < 10:
            return None

        attacker.ep -= 10
        attacker.shield_active = True
        msg = (
            f"🛡️ **{attacker.member.display_name}**: Kalkan kaldırdı! "
            f"(Gelecek saldırı `%80` zayıflatılacak + `5` yansıma)"
        )
        self._log(msg)
        self._next_turn()
        return msg

    # ── Eylem: İksir (İyileşme) ────────────────────────────────────────────────

    def action_potion(self) -> str | None:
        """
        🧪 20–30 HP yeniler. Maç başına 2 kullanım hakkı.
        Enerji harcamaz. Maksimum 100 HP'yi geçemez.
        Hakkı bittiyse None döner.
        """
        attacker = self.current
        if attacker.potions_left <= 0:
            return None

        attacker.potions_left -= 1
        heal = random.randint(20, 30)
        before = attacker.hp
        attacker.hp = min(attacker.max_hp, attacker.hp + heal)
        actual = attacker.hp - before
        msg = (
            f"🧪 **{attacker.member.display_name}**: İksir içti ve "
            f"`{actual}` HP yeniledi! (Kalan: `{attacker.potions_left}/2`)"
        )
        self._log(msg)
        self._next_turn()
        return msg

    # ── Bitiş Kontrolü ─────────────────────────────────────────────────────────

    def check_end(self) -> bool:
        """
        Oyunun bitip bitmediğini kontrol eder.
        Önce hedefin ölümünü kontrol eder: öldürme vuruşu her zaman kazandırır
        (yansıma hasarının aynı anda öldürmesi durumunda saldıran öncelikli).
        """
        if self.opponent.hp <= 0:
            self.finished = True
            self.winner = self.challenger
            self._log(f"🏆 **{self.winner.member.display_name}** kazandı!")
            return True
        if self.challenger.hp <= 0:
            self.finished = True
            self.winner = self.opponent
            self._log(f"🏆 **{self.winner.member.display_name}** kazandı!")
            return True
        return False


# ────────────────────────────────────────────────────────────────────────────────
#  ChallengeView — Meydan Okuma (Kabul / Red)
# ────────────────────────────────────────────────────────────────────────────────

class ChallengeView(discord.ui.View):
    """Rakibin savaş davetini kabul etmesini veya reddetmesini sağlayan View."""

    def __init__(self, challenger: discord.Member, opponent: discord.Member, cog: "Arena"):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent
        self.cog = cog
        self.message: discord.Message | None = None

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(content="⏰ Davet süresi doldu.", view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.challenger.id, self.opponent.id):
            await interaction.response.send_message("Bu davet sana değil!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Kabul Et", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, interaction: discord.Interaction, _: discord.ui.Button):
        # Sadece davet edilen rakip kabul edebilir
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "❌ Sadece davet edilen kişi kabul edebilir.", ephemeral=True
            )
            return

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=f"⚔️ Savaş başlıyor! **{self.challenger.display_name}** vs **{self.opponent.display_name}**",
            view=self,
        )

        # Oyunu ve savaş View'ini oluştur
        game = ArenaGame(self.challenger, self.opponent)
        battle_view = BattleView(game, self.cog)
        embed = battle_view.build_embed()

        msg = await interaction.followup.send(embed=embed, view=battle_view)
        battle_view.message = msg

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "❌ Sadece davet edilen kişi reddedebilir.", ephemeral=True
            )
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"❌ **{self.opponent.display_name}** daveti reddetti.",
            view=self,
        )
        self.stop()


# ────────────────────────────────────────────────────────────────────────────────
#  BattleView — Savaş Arayüzü (4 Aksiyon Butonu)
# ────────────────────────────────────────────────────────────────────────────────

class BattleView(discord.ui.View):
    """
    Savaşın ana arayüzüdür. 4 aksiyon butonu, durum embed'i ve
    bot sırasıysa otomatik hamle mekanizmasını barındırır.
    """

    def __init__(self, game: ArenaGame, cog: "Arena"):
        super().__init__(timeout=180)
        self.game = game
        self.cog = cog
        self.message: discord.Message | None = None
        self._bot_task: asyncio.Task | None = None

    # ── Embed Oluşturucu ──────────────────────────────────────────────────────

    def build_embed(self) -> discord.Embed:
        g = self.game
        p1, p2 = g.challenger, g.opponent

        if g.finished and g.winner:
            embed = discord.Embed(
                title=f"🏆 {g.winner.member.display_name} Kazandı!",
                color=discord.Color.gold(),
            )
        else:
            embed = discord.Embed(
                title=f"⚔️ Arena Savaşı — Tur {g.turn_count}",
                color=0xB41E1E,
            )

        def bar(val: int, max_val: int, length: int = 10) -> str:
            ratio = val / max_val if max_val else 0
            filled = max(0, min(length, int(ratio * length)))
            return f"{'█' * filled}{'░' * (length - filled)}"

        # Meydan okuyan (P1) durum kartı
        p1_lines = [
            f"❤️ HP: {bar(p1.hp, p1.max_hp)} `{p1.hp}/{p1.max_hp}`",
            f"⚡ EP: {bar(p1.ep, p1.max_ep)} `{p1.ep}/{p1.max_ep}`",
            f"🧪 İksir: `{'🟢' * p1.potions_left}{'⚫' * (2 - p1.potions_left)}`  ({p1.potions_left}/2)",
        ]
        if p1.shield_active:
            p1_lines.append("🛡️ **Kalkan aktif!**")

        # Rakip (P2) durum kartı
        p2_lines = [
            f"❤️ HP: {bar(p2.hp, p2.max_hp)} `{p2.hp}/{p2.max_hp}`",
            f"⚡ EP: {bar(p2.ep, p2.max_ep)} `{p2.ep}/{p2.max_ep}`",
            f"🧪 İksir: `{'🟢' * p2.potions_left}{'⚫' * (2 - p2.potions_left)}`  ({p2.potions_left}/2)",
        ]
        if p2.shield_active:
            p2_lines.append("🛡️ **Kalkan aktif!**")

        embed.add_field(
            name=f"🟢 {p1.member.display_name}",
            value="\n".join(p1_lines),
            inline=True,
        )
        embed.add_field(name="VS", value="⚔️", inline=True)
        embed.add_field(
            name=f"🔴 {p2.member.display_name}",
            value="\n".join(p2_lines),
            inline=True,
        )

        # Sıra göstergesi
        if not g.finished:
            turn_emoji = "🤖" if g.current.is_bot else "🎯"
            embed.add_field(
                name="🎲 Sıra",
                value=f"{turn_emoji} **{g.current.member.display_name}** hamle yapıyor...",
                inline=False,
            )

        # Savaş günlüğü (son 5 kayıt)
        if g.log:
            log_text = "\n".join(f"> *{line}*" for line in g.log[-5:])
        else:
            log_text = "> *Savaş alanına hoş geldiniz... İlk hamle meydan okuyana ait!*"
        embed.add_field(name="📜 Savaş Günlüğü", value=log_text, inline=False)

        embed.set_footer(text="Sıranı bekle • Her aksiyon bir tur harcar • 3 dakika süre sınırı")
        return embed

    # ── Bot AI ────────────────────────────────────────────────────────────────

    def _bot_decide(self) -> str:
        """
        Botun hamle seçimini yapan basit yapay zeka.
        Öncelikler: İyileşme > Bitirici vuruş > Büyü > Kalkan > Kılıç.
        """
        bot = self.game.current
        opp = self.game.other

        # 1. Ölümcül durumda iyileş
        if bot.hp <= 25 and bot.potions_left > 0:
            return "potion"

        # 2. Rakibi öldürebilirsek güçlü hamle kullan
        if opp.hp <= 18:
            if bot.ep >= 20:
                return "spell"
            return "sword"

        # 3. Yeterli enerji varsa büyü (yüksek hasar)
        if bot.ep >= 20 and opp.hp >= 30:
            return "spell"

        # 4. EP azaldıysa kılıçla enerji topla
        if bot.ep < 15:
            return "sword"

        # 5. Pot yoksa ve can düşükse, ara sıra kalkan kullan
        if bot.ep >= 10 and bot.potions_left == 0 and bot.hp < 50 and random.random() < 0.35:
            return "shield"

        # 6. Varsayılan: güvenli tercih
        return "sword"

    # ── Hamle İşleyici ─────────────────────────────────────────────────────────

    async def _execute_action(self, action: str, interaction: discord.Interaction | None) -> None:
        """
        Bir aksiyonu çalıştırır, embed'i günceller ve oyun bittiğini kontrol eder.
        interaction=None ise bot hamlesidir; mesaj doğrudan editlenir.
        """
        g = self.game
        current = g.current

        # ── Kaynak kontrolü (yetersizse tur geçişi olmaz) ──────────────────────
        if action == "spell" and current.ep < 20:
            if interaction:
                await interaction.response.send_message(
                    "🔮 Büyü kullanmak için `20` EP gerekli!", ephemeral=True
                )
            return

        if action == "shield" and current.ep < 10:
            if interaction:
                await interaction.response.send_message(
                    "🛡️ Kalkan kullanmak için `10` EP gerekli!", ephemeral=True
                )
            return

        if action == "potion" and current.potions_left <= 0:
            if interaction:
                await interaction.response.send_message(
                    "🧪 İksir hakkın kalmadı!", ephemeral=True
                )
            return

        # ── Hamleyi uygula ──────────────────────────────────────────────────────
        if action == "sword":
            g.action_sword()
        elif action == "spell":
            g.action_spell()
        elif action == "shield":
            g.action_shield()
        elif action == "potion":
            g.action_potion()

        # ── Oyun bitti mi? ──────────────────────────────────────────────────────
        if g.check_end():
            for child in self.children:
                child.disabled = True
            self.stop()
            embed = self.build_embed()
            if interaction and not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=self)
            elif self.message:
                await self.message.edit(embed=embed, view=self)
            return

        # ── Normal güncelleme ───────────────────────────────────────────────────
        embed = self.build_embed()
        if interaction and not interaction.response.is_done():
            await interaction.response.edit_message(embed=embed, view=self)
        elif self.message:
            await self.message.edit(embed=embed, view=self)

        # ── Sıradaki bot mu? Otomatik hamle tetikle ─────────────────────────────
        if g.current.is_bot and not g.finished:
            self._bot_task = asyncio.create_task(self._bot_turn())

    async def _bot_turn(self) -> None:
        """Botun "düşünme" süresi sonrası otomatik hamle yapmasını sağlar."""
        await asyncio.sleep(1.5)
        if self.game.finished or self.is_finished():
            return

        # Bot düşünürken butonları geçici olarak pasifleştir (spam koruması)
        for child in self.children:
            child.disabled = True
        embed = self.build_embed()
        if self.message:
            await self.message.edit(embed=embed, view=self)

        await asyncio.sleep(0.8)
        if self.game.finished or self.is_finished():
            return

        action = self._bot_decide()
        await self._execute_action(action, None)

        # Bot hamlesi bitti, butonları tekrar aktif et (eğer oyun bitmediyse)
        if not self.game.finished:
            for child in self.children:
                child.disabled = False
            embed = self.build_embed()
            if self.message:
                await self.message.edit(embed=embed, view=self)

    # ── View Callback'leri ──────────────────────────────────────────────────────

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Sadece sırası gelen oyuncunun butona basmasına izin verir."""
        if self.game.finished:
            return False
        expected_id = self.game.current.member.id
        if interaction.user.id != expected_id:
            await interaction.response.send_message(
                "⛔ Sıra sende değil! Rakibin hamlesini bekle.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Kılıç", emoji="⚔️", style=discord.ButtonStyle.danger, row=0)
    async def sword_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._execute_action("sword", interaction)

    @discord.ui.button(label="Büyü", emoji="🔮", style=discord.ButtonStyle.primary, row=0)
    async def spell_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._execute_action("spell", interaction)

    @discord.ui.button(label="Kalkan", emoji="🛡️", style=discord.ButtonStyle.secondary, row=1)
    async def shield_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._execute_action("shield", interaction)

    @discord.ui.button(label="İksir", emoji="🧪", style=discord.ButtonStyle.success, row=1)
    async def potion_btn(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._execute_action("potion", interaction)

    async def on_timeout(self) -> None:
        if self._bot_task and not self._bot_task.done():
            self._bot_task.cancel()
        for child in self.children:
            child.disabled = True
        if self.message:
            embed = self.build_embed()
            embed.title = "⏰ Süre Doldu — Savaş Sonlandırıldı"
            embed.color = discord.Color.dark_grey()
            await self.message.edit(embed=embed, view=self)


# ────────────────────────────────────────────────────────────────────────────────
#  Arena Cog
# ────────────────────────────────────────────────────────────────────────────────

class Arena(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="arena",
        description="Bir oyuncuyla veya botla taktiksel arena savaşı yap!",
    )
    @app_commands.describe(rakip="Dövüşmek istediğin kişi (boş bırakırsan botla savaşırsın)")
    @app_commands.guild_only()
    async def arena(
        self,
        interaction: discord.Interaction,
        rakip: discord.Member | None = None,
    ):
        # ── Bot ile savaş (anlık başlangıç) ────────────────────────────────────
        if rakip is None:
            bot_member = interaction.guild.me
            game = ArenaGame(interaction.user, bot_member, is_vs_bot=True)
            view = BattleView(game, self)
            embed = view.build_embed()

            await interaction.response.send_message(embed=embed, view=view)
            view.message = await interaction.original_response()
            return

        # ── Kendine savaş kontrolü ─────────────────────────────────────────────
        if rakip.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ Kendinle savaşamazsın!", ephemeral=True
            )
            return

        # ── Başka bir bota meydan okuma engeli ─────────────────────────────────
        if rakip.bot:
            await interaction.response.send_message(
                "❌ Botlarla savaşamazsın! `/arena` yazarak kendi botunla savaşabilirsin.",
                ephemeral=True,
            )
            return

        # ── İnsan rakibe davet gönder ────────────────────────────────────────────
        view = ChallengeView(interaction.user, rakip, self)
        await interaction.response.send_message(
            content=f"🎯 {rakip.mention}, **{interaction.user.display_name}** seni arena savaşına davet ediyor!",
            embed=discord.Embed(
                description="Aşağıdaki butonlardan birini seç.",
                color=0xB41E1E,
            ),
            view=view,
        )
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(Arena(bot))
