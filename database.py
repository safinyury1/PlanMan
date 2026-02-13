import aiosqlite

DB_NAME = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                remind_minutes INTEGER DEFAULT 15,
                calendar_token TEXT
            )
        """)
        await db.commit()

async def set_token(user_id: int, token_json: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO users (user_id, calendar_token) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET calendar_token = ?",
            (user_id, token_json, token_json)
        )
        await db.commit()

async def set_reminder(user_id: int, minutes: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET remind_minutes = ? WHERE user_id = ?",
            (minutes, user_id)
        )
        await db.commit()

async def get_user_data(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT remind_minutes, calendar_token FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, calendar_token, remind_minutes FROM users") as cursor:
            return await cursor.fetchall()