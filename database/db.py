import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    return db


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS infractions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                mod_id      INTEGER NOT NULL,
                reason      TEXT,
                type        TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_commands (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER NOT NULL,
                name        TEXT NOT NULL,
                response    TEXT NOT NULL,
                created_by  INTEGER NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, name)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS mutes (
                guild_id    INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                unmute_at   TIMESTAMP NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        await db.commit()


# --- Infractions ---

async def add_infraction(guild_id: int, user_id: int, mod_id: int, reason: str, itype: str):
    async with await get_db() as db:
        await db.execute(
            "INSERT INTO infractions (guild_id, user_id, mod_id, reason, type) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, mod_id, reason, itype),
        )
        await db.commit()


async def get_infractions(guild_id: int, user_id: int):
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM infractions WHERE guild_id=? AND user_id=? ORDER BY created_at DESC",
            (guild_id, user_id),
        )
        return await cursor.fetchall()


async def clear_infractions(guild_id: int, user_id: int):
    async with await get_db() as db:
        await db.execute(
            "DELETE FROM infractions WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )
        await db.commit()


# --- Custom Commands ---

async def create_custom_command(guild_id: int, name: str, response: str, created_by: int):
    async with await get_db() as db:
        await db.execute(
            "INSERT INTO custom_commands (guild_id, name, response, created_by) VALUES (?, ?, ?, ?)",
            (guild_id, name, response, created_by),
        )
        await db.commit()


async def get_custom_command(guild_id: int, name: str):
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM custom_commands WHERE guild_id=? AND name=?",
            (guild_id, name),
        )
        return await cursor.fetchone()


async def list_custom_commands(guild_id: int):
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT name, response, created_by, created_at FROM custom_commands WHERE guild_id=? ORDER BY name",
            (guild_id,),
        )
        return await cursor.fetchall()


async def delete_custom_command(guild_id: int, name: str):
    async with await get_db() as db:
        cursor = await db.execute(
            "DELETE FROM custom_commands WHERE guild_id=? AND name=?",
            (guild_id, name),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_command_names(guild_id: int):
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT name FROM custom_commands WHERE guild_id=?",
            (guild_id,),
        )
        rows = await cursor.fetchall()
        return [row["name"] for row in rows]
