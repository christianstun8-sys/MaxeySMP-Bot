import aiosqlite

async def config_setup_db(db: aiosqlite.Connection):
    await db.execute("""CREATE TABLE IF NOT EXISTS roles (
                                                             guild_id INTEGER PRIMARY KEY,
                                                             moderator_id INTEGER,
                                                             administrator_id INTEGER,
                                                             team_lead_id INTEGER,
                                                             sr_mod_id INTEGER,
                                                             developer_id INTEGER,
                                                             content_creator_id INTEGER,
                                                             staff_id INTEGER,
                                                             vip_id INTEGER,
                                                             sub_id INTEGER,
                                                             booster_id INTEGER,
                                                             member_id INTEGER,
                                                             builder_id INTEGER,
                                                             update_ping_id INTEGER
                        )""")
    await db.execute("""INSERT OR IGNORE INTO roles (guild_id) VALUES (?)""", (1476359827176423426,))
    await db.execute("""INSERT OR IGNORE INTO roles(guild_id) VALUES (?)""", (1133464786252861633,))
    await db.execute("""CREATE TABLE IF NOT EXISTS channels (
                                                                guild_id INTEGER PRIMARY KEY,
                                                                faq_channel_id INTEGER,
                                                                ticket_panel_channel_id INTEGER,
                                                                member_counter_channel_id INTEGER,
                                                                ticket_logs_channel_id INTEGER,
                                                                welcome_channel_id INTEGER,
                                                                role_panel_channel_id INTEGER,
                                                                level_up_channel_id INTEGER,
                                                                counting_channel_id INTEGER,
                                                                link_panel_channel_id INTEGER,
                                                                rule_panel_channel_id INTEGER)
                     """)
    await db.execute("""INSERT OR IGNORE INTO channels(guild_id ) VALUES (?)""", (1476359827176423426,))
    await db.execute("""INSERT OR IGNORE INTO channels(guild_id) VALUES (?)""", (1133464786252861633,))
    await db.execute("""CREATE TABLE IF NOT EXISTS categories (
                                                                guild_id INTEGER PRIMARY KEY,
                                                                open_tickets_cat_id INTEGER,
                                                                closed_tickets_cat_id INTEGER,
                                                                claimed_tickets_cat_id INTEGER)""")
    await db.execute("""INSERT OR IGNORE INTO categories(guild_id) VALUES (?)""", (1476359827176423426,))
    await db.execute("""INSERT OR IGNORE INTO categories(guild_id) VALUES (?)""", (1133464786252861633,))
    await db.execute("""CREATE TABLE IF NOT EXISTS spam(
                                                            guild_id INTEGER PRIMARY KEY,
                                                            messages_in_a_row INTEGER,
                                                            timewindow INTEGER)""")
    await db.execute("""INSERT OR IGNORE INTO spam(guild_id) VALUES (?)""", (1476359827176423426,))
    await db.execute("""INSERT OR IGNORE INTO spam(guild_id) VALUES (?)""", (1133464786252861633,))
    await db.execute("""CREATE TABLE IF NOT EXISTS counting(
                                                            guild_id INTEGER PRIMARY KEY,
                                                            calculation INTEGER
                        )""")
    await db.execute("""INSERT OR IGNORE INTO counting(guild_id, calculation) VALUES (?, ?)""", (1476359827176423426, 0,))
    await db.execute("""INSERT OR IGNORE INTO counting(guild_id, calculation) VALUES (?, ?)""", (1133464786252861633, 0,))
    await db.execute("""CREATE TABLE IF NOT EXISTS messages(
                                                            guild_id INTEGER PRIMARY KEY,
                                                            welcome_message TEXT,
                                                            link_mc_message TEXT,
                                                            ticket_panel_message TEXT
                        )""")
    await db.execute("""INSERT OR IGNORE INTO messages(guild_id) VALUES (?)""", (1476359827176423426, ))
    await db.execute("""INSERT OR IGNORE INTO messages(guild_id) VALUES (?)""", (1133464786252861633, ))
    await db.execute("""CREATE TABLE IF NOT EXISTS link_mc_db(
                                                                host TEXT,
                                                                port INTEGER,
                                                                db_name TEXT,
                                                                username TEXT,
                                                                password TEXT)""")
    await db.execute("""CREATE TABLE IF NOT EXISTS syncroles_webserver(
                                                                        url TEXT,
                                                                        password TEXT)""")
    await db.commit()

async def get_role_config(db: aiosqlite.Connection, guild_id: int):
    async with db.execute("""SELECT * FROM roles WHERE guild_id = ?""", (guild_id,)) as cursor:
        return await cursor.fetchone()

async def get_channel_config(db: aiosqlite.Connection, guild_id: int):
    async with db.execute("""SELECT * FROM channels WHERE guild_id = ?""", (guild_id,)) as cursor:
        return await cursor.fetchone()

async def get_category_config(db: aiosqlite.Connection, guild_id: int):
    async with db.execute("""SELECT * FROM categories WHERE guild_id = ?""", (guild_id,)) as cursor:
        return await cursor.fetchone()

async def get_spam_config(db: aiosqlite.Connection, guild_id: int):
    async with db.execute("""SELECT * FROM spam WHERE guild_id = ?""", (guild_id,)) as cursor:
        return await cursor.fetchone()

async def get_counting_config(db: aiosqlite.Connection, guild_id: int):
    async with db.execute("""SELECT * FROM counting WHERE guild_id = ?""", (guild_id,)) as cursor:
        return await cursor.fetchone()

async def get_message_config(db: aiosqlite.Connection, guild_id: int):
    async with db.execute("""SELECT * FROM messages WHERE guild_id = ?""", (guild_id,)) as cursor:
        return await cursor.fetchone()

async def get_link_db_config(db: aiosqlite.Connection):
    async with db.execute("""SELECT * FROM link_mc_db""") as cursor:
        return await cursor.fetchone()

async def get_syncroles_webserver_config(db: aiosqlite.Connection):
    async with db.execute("""SELECT * FROM syncroles_webserver""") as cursor:
        return await cursor.fetchone()