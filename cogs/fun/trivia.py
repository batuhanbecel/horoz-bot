"""
cogs/fun/trivia.py — Bilgi yarışması (Türkçe, interaktif butonlar)
"""
from __future__ import annotations

import logging
import random

import discord
from discord import app_commands
from discord.ext import commands
from .._v2 import c_container, c_separator, c_text, respond

log = logging.getLogger("horoz_bot.trivia")

_TRIVIA = [
    {"soru": "Türkiye'nin en yüksek dağı hangisidir?", "secenekler": ["Ağrı Dağı", "Uludağ", "Erciyes", "Kaçkar Dağı"], "dogru": 0},
    {"soru": "İstanbul'un fethi hangi yılda gerçekleşmiştir?", "secenekler": ["1451", "1453", "1455", "1460"], "dogru": 1},
    {"soru": "Türk bayrağındaki ay ve yıldızın rengi nedir?", "secenekler": ["Sarı", "Beyaz", "Kırmızı", "Siyah"], "dogru": 1},
    {"soru": "Türkiye'nin başkenti hangi şehirdir?", "secenekler": ["İstanbul", "İzmir", "Ankara", "Bursa"], "dogru": 2},
    {"soru": "Nutuk hangi yılda söylenmiştir?", "secenekler": ["1920", "1923", "1927", "1934"], "dogru": 2},
    {"soru": "Dünya'nın en büyük okyanusu hangisidir?", "secenekler": ["Atlantik", "Hint", "Pasifik", "Arktik"], "dogru": 2},
    {"soru": "Python programlama dili hangi yılda yayımlanmıştır?", "secenekler": ["1989", "1991", "1995", "2000"], "dogru": 1},
    {"soru": "Türkiye'nin en uzun nehri hangisidir?", "secenekler": ["Fırat", "Dicle", "Kızılırmak", "Sakarya"], "dogru": 2},
    {"soru": "Işık hızı yaklaşık kaç km/s'dir?", "secenekler": ["150.000", "300.000", "500.000", "1.000.000"], "dogru": 1},
    {"soru": "Dünya'nın uydusu hangisidir?", "secenekler": ["Mars", "Venüs", "Ay", "Jüpiter"], "dogru": 2},
    {"soru": "Bir yılda kaç gün vardır?", "secenekler": ["364", "365", "366", "360"], "dogru": 1},
    {"soru": "İnsan vücudundaki en büyük organ hangisidir?", "secenekler": ["Karaciğer", "Deri", "Akciğer", "Beyin"], "dogru": 1},
    {"soru": "H2O hangi maddenin kimyasal formülüdür?", "secenekler": ["Su", "Tuz", "Kum", "Demir"], "dogru": 0},
    {"soru": "Dünya'nın en yüksek dağı hangisidir?", "secenekler": ["K2", "Everest", "Kilimanjaro", "Mont Blanc"], "dogru": 1},
]


class TriviaAnswerButton(discord.ui.Button):
    def __init__(self, index: int, cog: "Trivia"):
        label = f"{index + 1}"
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=0)
        self.index = index
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, TriviaView):
            return
        question = view.question
        correct_idx = question["dogru"]

        for child in view.children:
            if isinstance(child, TriviaAnswerButton):
                child.disabled = True
                if child.index == correct_idx:
                    child.style = discord.ButtonStyle.success
                elif child.index == self.index and self.index != correct_idx:
                    child.style = discord.ButtonStyle.danger
                else:
                    child.style = discord.ButtonStyle.secondary

        body_lines = [f"**{question['soru']}**"]
        for i, opt in enumerate(question["secenekler"]):
            prefix = "✅" if i == correct_idx else ("❌" if i == self.index else "◻️")
            body_lines.append(f"{prefix} {i + 1}. {opt}")
        if self.index == correct_idx:
            body_lines.append("\n🎉 Doğru cevap!")
        else:
            body_lines.append(f"\n❌ Yanlış! Doğru cevap: **{question['secenekler'][correct_idx]}**")
        body = "\n".join(body_lines)

        container = c_container(
            c_text(f"## ❓ Trivia\n\n{body}"),
            c_separator(),
            c_text("-# 🔄 Yeni soru için butona basın"),
        )
        await self.cog._patch_message(interaction, container, view)


class TriviaNewButton(discord.ui.Button):
    def __init__(self, cog: "Trivia"):
        super().__init__(label="🔄 Yeni Soru", style=discord.ButtonStyle.primary, row=1)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await self.cog._send_question(interaction)


class TriviaView(discord.ui.View):
    def __init__(self, question: dict, cog: "Trivia"):
        super().__init__(timeout=120)
        self.question = question
        for i in range(len(question["secenekler"])):
            self.add_item(TriviaAnswerButton(i, cog))
        self.add_item(TriviaNewButton(cog))


class Trivia(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="trivia", description="Rastgele bir bilgi yarışması sorusu")
    async def trivia(self, interaction: discord.Interaction):
        await self._send_question(interaction)

    async def _send_question(self, interaction: discord.Interaction):
        soru = random.choice(_TRIVIA)
        view = TriviaView(soru, self)
        body_lines = [f"**{soru['soru']}**"]
        for i, opt in enumerate(soru["secenekler"]):
            body_lines.append(f"{i + 1}. {opt}")
        body = "\n".join(body_lines)
        container = c_container(
            c_text(f"## ❓ Trivia\n\n{body}"),
            c_separator(),
            c_text("-# Doğru cevabı seçin!"),
        )
        if interaction.type == discord.InteractionType.component:
            # Button click: edit existing message
            if not interaction.response.is_done():
                await interaction.response.edit_message(
                    components=[container.to_component_dict()], view=view
                )
            else:
                await interaction.edit_original_response(
                    components=[container.to_component_dict()], view=view
                )
        else:
            msg = await respond(interaction, container, view=view)
            if msg:
                interaction._state.store_view(view, msg.id)

    async def _patch_message(
        self,
        interaction: discord.Interaction,
        container: discord.ui.Container,
        view: discord.ui.View,
    ) -> None:
        """Edit the message for a button click (answer reveal)."""
        if not interaction.response.is_done():
            await interaction.response.edit_message(
                components=[container.to_component_dict()], view=view
            )
        else:
            await interaction.edit_original_response(
                components=[container.to_component_dict()], view=view
            )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("trivia hatası: %s", error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Trivia(bot))
