import re
import discord
from discord.ext import commands

# Önce daha uzun / spesifik pattern'lar, sonra genel kelimeler.
GREETING_MAP = [
    (re.compile(r"\bselamun aleyküm\b", re.I), "Aleyküm selam"),
    (re.compile(r"\bselamın aleyküm\b", re.I), "Aleyküm selam"),
    (re.compile(r"\bselamlar\b", re.I), "Selam"),
    (re.compile(r"\bselam\b", re.I), "Aleyküm selam"),
    (re.compile(r"\bmerhabalar\b", re.I), "Merhaba"),
    (re.compile(r"\bmerhaba\b", re.I), "Merhaba"),
    (re.compile(r"\bhello\b", re.I), "Hello"),
    (re.compile(r"\bhi\b", re.I), "Hi"),
    (re.compile(r"\bhey\b", re.I), "Hey"),
    (re.compile(r"\bhola\b", re.I), "Hola"),
    (re.compile(r"\bslm\b", re.I), "Selam"),
    (re.compile(r"\bmrb\b", re.I), "Merhaba"),
    (re.compile(r"\bmrlb\b", re.I), "Merhaba"),
    (re.compile(r"\bs\.a\.\b", re.I), "Aleyküm selam"),
    (re.compile(r"\bs\.a\b", re.I), "Aleyküm selam"),
    (re.compile(r"\bsa\b", re.I), "Aleyküm selam"),
]

class Greetings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content = message.content
        for pattern, reply in GREETING_MAP:
            if pattern.search(content):
                await message.channel.send(f"Ü ürü üüü! {reply}")
                return


async def setup(bot: commands.Bot):
    await bot.add_cog(Greetings(bot))
