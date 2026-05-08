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
        if py.name.startswith("_") or py.stem == "views":
            continue
        # cogs/server/emoji.py  →  cogs.server.emoji
        found.append(".".join(py.with_suffix("").parts))
    return found


class HorozBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            allowed_mentions=discord.AllowedMentions.none(),
            command_sync_flag=commands.CommandSyncFlag.sync,
            max_messages=10000,
        )
        self._app_info: discord.AppInfo | None = None

    async def setup_hook(self):
        from database.db import init_db
        await init_db()

        # Global error handler cog — diğer tüm cog'lardan önce yükle
        try:
            await self.load_extension("cogs.error_handler")
            log.info("Yüklendi: cogs.error_handler")
        except Exception as e:
            log.warning(f"Error handler yüklénemedi: {e}")

        for cog in discover_cogs():
            if cog == "cogs.error_handler":
                continue
            try:
                await self.load_extension(cog)
                log.info(f"Yüklendi: {cog}")
            except Exception as e:
                log.error(f"Yüklenemedi {cog}: {e}")

        # Guild-specific sync (modern discord.py 2.5+)
        await self.tree.sync()
        log.info("Slash komutlar senkronize edildi.")

    async def on_ready(self):
        self._app_info = await self.application_info()
        flags: list[str] = []
        if self._app_info.bot_public:
            flags.append("public")
        if self._app_info.bot_require_code_grant:
            flags.append("code-grant")

        log.info(
            f"{self.user} olarak giriş yapıldı "
            f"(ID: {self.user.id} · {len(self.guilds)} sunucu · flags: {', '.join(flags) or 'none'})"
        )
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/yardım | Horoz Bot v2",
            ),
            status=discord.Status.online,
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
