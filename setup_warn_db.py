import aiosqlite

async def warn_setup_db(db: aiosqlite.Connection):
    await db.execute("""CREATE TABLE IF NOT EXISTS warns (
                                                            user_id INTEGER PRIMARY KEY,
                                                            warns INTEGER)""")
    await db.commit()

async def get_warns(db: aiosqlite.Connection, user_id: int):
    async with db.execute("SELECT warns FROM warns WHERE user_id = ?", (user_id,)) as cursor:
        return await cursor.fetchone()

async def warn_someone(db: aiosqlite.Connection, user_id: int):
    await db.execute("""INSERT INTO warns(user_id, warns) VALUES (?, 1)""", (user_id,))
    await db.commit()