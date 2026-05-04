import discord
from discord.ext import commands
import asyncio
import os
import pathlib
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("horoz_bot")


def discover_cogs() -> list[str]:
    """cogs/ altındaki tüm alt-klasör .py dosyalarını otomatik bulur."""
    found = []
    for py in sorted(pathlib.Path("cogs").rglob("*.py")):
        if py.name.startswith("_"):
            continue
        # cogs/server/emoji.py  →  cogs.server.emoji
        found.append(".".join(py.with_suffix("").parts))
    return found


class HorozBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)

    async def setup_hook(self):
        from database.db import init_db
        await init_db()

        for cog in discover_cogs():
            try:
                await self.load_extension(cog)
                log.info(f"Yüklendi: {cog}")
            except Exception as e:
                log.error(f"Yüklenemedi {cog}: {e}")

        await self.tree.sync()
        log.info("Slash komutlar senkronize edildi.")

    async def on_ready(self):
        log.info(f"{self.user} olarak giriş yapıldı (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/yardım | Horoz Bot",
            )
        )


async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        log.critical("DISCORD_TOKEN bulunamadı! .env dosyasını kontrol et.")
        return

    async with HorozBot() as bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
