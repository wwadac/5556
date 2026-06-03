import aiosqlite
import logging

DB_PATH = "phoenix_tasks.db"
logger = logging.getLogger(__name__)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                minecraft_nick TEXT DEFAULT '',
                balance     INTEGER DEFAULT 0,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_submissions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                photo_id    TEXT,
                status      TEXT DEFAULT 'pending',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER,
                amount          INTEGER,
                minecraft_nick  TEXT,
                status          TEXT DEFAULT 'pending',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    logger.info("Database initialized.")

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def create_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username or "", full_name or "")
        )
        await db.commit()

async def update_user(user_id: int, **kwargs):
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {sets} WHERE user_id = ?", values)
        await db.commit()

async def add_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def subtract_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def add_submission(user_id: int, photo_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO task_submissions (user_id, photo_id) VALUES (?, ?)", (user_id, photo_id))
        await db.commit()
        return cursor.lastrowid

async def get_submission(sub_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM task_submissions WHERE id = ?", (sub_id,))
        return await cursor.fetchone()

async def update_submission(sub_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE task_submissions SET status = ? WHERE id = ?", (status, sub_id))
        await db.commit()

async def add_withdraw_request(user_id: int, amount: int, nick: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO withdraw_requests (user_id, amount, minecraft_nick) VALUES (?, ?, ?)",
            (user_id, amount, nick)
        )
        await db.commit()
        return cursor.lastrowid

async def get_withdraw_request(req_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM withdraw_requests WHERE id = ?", (req_id,))
        return await cursor.fetchone()

async def update_withdraw_request(req_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE withdraw_requests SET status = ? WHERE id = ?", (status, req_id))
        await db.commit()