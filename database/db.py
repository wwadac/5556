"""Работа с базой данных"""
import aiosqlite
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import config


class Database:
    def __init__(self):
        self.db_path = config.DB_PATH

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    trial_until TIMESTAMP,
                    subscribed_until TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    payment_code TEXT UNIQUE,
                    payment_status TEXT DEFAULT 'none'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dialogs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER,
                    chat_id INTEGER,
                    peer_id INTEGER,
                    peer_name TEXT,
                    peer_username TEXT,
                    last_message_at TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    UNIQUE(owner_id, chat_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_id INTEGER,
                    chat_id INTEGER,
                    message_id INTEGER,
                    from_user_id INTEGER,
                    from_user_name TEXT,
                    text TEXT,
                    media_type TEXT,
                    media_file_id TEXT,
                    caption TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    edited_at TIMESTAMP,
                    is_deleted INTEGER DEFAULT 0,
                    is_outgoing INTEGER DEFAULT 0,
                    FOREIGN KEY (owner_id) REFERENCES users(user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS edit_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    chat_id INTEGER,
                    owner_id INTEGER,
                    old_text TEXT,
                    new_text TEXT,
                    edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    code TEXT,
                    amount INTEGER,
                    status TEXT DEFAULT 'pending',
                    screenshot_file_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    verified_at TIMESTAMP
                )
            """)
            await db.commit()

    # === USERS ===
    async def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        trial_until = datetime.now() + timedelta(hours=config.TRIAL_HOURS)
        payment_code = f"{random.randint(1000, 9999)}"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users
                (user_id, username, first_name, last_name, trial_until, payment_code)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, first_name, last_name, trial_until, payment_code))
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_all_users(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users") as cursor:
                return [dict(row) async for row in cursor]

    async def get_stats(self) -> Dict[str, int]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                total = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE is_active = 1") as cursor:
                active = (await cursor.fetchone())[0]
            return {"total": total, "active": active}

    async def is_subscribed(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False
        now = datetime.now()
        if user["trial_until"] and datetime.fromisoformat(user["trial_until"]) > now:
            return True
        if user["subscribed_until"] and datetime.fromisoformat(user["subscribed_until"]) > now:
            return True
        return False

    async def activate_subscription(self, user_id: int, days: int = None):
        if days is None:
            days = config.SUBSCRIPTION_DAYS
        subscribed_until = datetime.now() + timedelta(days=days)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users SET subscribed_until = ?, payment_status = 'paid'
                WHERE user_id = ?
            """, (subscribed_until, user_id))
            await db.commit()

    # === DIALOGS ===
    async def add_or_update_dialog(self, owner_id: int, chat_id: int, peer_id: int,
                                    peer_name: str, peer_username: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO dialogs (owner_id, chat_id, peer_id, peer_name, peer_username, last_message_at, message_count)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(owner_id, chat_id) DO UPDATE SET
                    peer_name = excluded.peer_name,
                    peer_username = excluded.peer_username,
                    last_message_at = excluded.last_message_at,
                    message_count = message_count + 1
            """, (owner_id, chat_id, peer_id, peer_name, peer_username, datetime.now()))
            await db.commit()

    async def get_dialogs(self, owner_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM dialogs WHERE owner_id = ? ORDER BY last_message_at DESC
            """, (owner_id,)) as cursor:
                return [dict(row) async for row in cursor]

    async def get_dialog(self, owner_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM dialogs WHERE owner_id = ? AND chat_id = ?", (owner_id, chat_id)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    # === MESSAGES ===
    async def save_message(self, owner_id: int, chat_id: int, message_id: int,
                          from_user_id: int, from_user_name: str, text: str = None,
                          media_type: str = None, media_file_id: str = None,
                          caption: str = None, is_outgoing: bool = False):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO messages
                (owner_id, chat_id, message_id, from_user_id, from_user_name, text, media_type, media_file_id, caption, is_outgoing)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (owner_id, chat_id, message_id, from_user_id, from_user_name, text,
                  media_type, media_file_id, caption, int(is_outgoing)))
            await db.commit()

    async def mark_deleted(self, message_id: int, chat_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE messages SET is_deleted = 1 WHERE message_id = ? AND chat_id = ?
            """, (message_id, chat_id))
            await db.commit()

    async def save_edit(self, message_id: int, chat_id: int, owner_id: int, old_text: str, new_text: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO edit_history (message_id, chat_id, owner_id, old_text, new_text)
                VALUES (?, ?, ?, ?, ?)
            """, (message_id, chat_id, owner_id, old_text, new_text))
            await db.execute("""
                UPDATE messages SET text = ?, edited_at = ? WHERE message_id = ? AND chat_id = ?
            """, (new_text, datetime.now(), message_id, chat_id))
            await db.commit()

    async def get_chat_messages(self, owner_id: int, chat_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM messages
                WHERE owner_id = ? AND chat_id = ? AND is_deleted = 0
                ORDER BY created_at ASC
            """, (owner_id, chat_id)) as cursor:
                return [dict(row) async for row in cursor]

    async def get_chat_stats(self, owner_id: int, chat_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM messages WHERE owner_id = ? AND chat_id = ? AND is_deleted = 0
            """, (owner_id, chat_id)) as cursor:
                total = (await cursor.fetchone())[0]
            async with db.execute("""
                SELECT COUNT(*) FROM messages WHERE owner_id = ? AND chat_id = ? AND is_deleted = 1
            """, (owner_id, chat_id)) as cursor:
                deleted = (await cursor.fetchone())[0]
            async with db.execute("""
                SELECT COUNT(*) FROM edit_history WHERE owner_id = ? AND chat_id = ?
            """, (owner_id, chat_id)) as cursor:
                edited = (await cursor.fetchone())[0]
            return {"total": total, "deleted": deleted, "edited": edited}

    async def get_total_messages(self, owner_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM messages WHERE owner_id = ?", (owner_id,)
            ) as cursor:
                return (await cursor.fetchone())[0]

    async def get_total_dialogs(self, owner_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM dialogs WHERE owner_id = ?", (owner_id,)
            ) as cursor:
                return (await cursor.fetchone())[0]

    # === PAYMENTS ===
    async def create_payment(self, user_id: int) -> str:
        code = f"{random.randint(1000, 9999)}"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO payments (user_id, code, amount) VALUES (?, ?, ?)
            """, (user_id, code, config.SUBSCRIPTION_PRICE))
            await db.commit()
        return code

    async def get_payment_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM payments WHERE code = ?", (code,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def add_screenshot(self, payment_id: int, file_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE payments SET screenshot_file_id = ?, status = 'waiting_verify' WHERE id = ?
            """, (file_id, payment_id))
            await db.commit()

    async def verify_payment(self, payment_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE payments SET status = 'verified', verified_at = ? WHERE id = ?
            """, (datetime.now(), payment_id))
            await db.commit()


db = Database()
