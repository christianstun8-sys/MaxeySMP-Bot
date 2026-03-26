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
                                                             member_id INTEGER
                        )""")
    await db.execute("""
                     INSERT OR IGNORE INTO roles (
                         guild_id, moderator_id, administrator_id, team_lead_id,
                         sr_mod_id, developer_id, content_creator_id, staff_id,
                         vip_id, sub_id, booster_id, member_id
                     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                     """, (
                            1476359827176423426,
                            1476361600540606504,
                            1476360446293577972,
                            1482342255854620692,
                            1482402217582526514,
                            1476658803813519392,
                            1477028784921247856,
                            1476360960141693069,
                            1476362014719869109,
                            1476364278784065677,
                            1479954718468997377,
                            1476364633483907103
                     ))
    await db.execute("""CREATE TABLE IF NOT EXISTS channels (
                                                                guild_id INTEGER PRIMARY KEY,
                                                                faq_channel_id INTEGER,
                                                                ticket_panel_channel_id INTEGER,
                                                                member_counter_channel_id INTEGER,
                                                                ticket_logs_channel_id INTEGER,
                                                                welcome_channel_id INTEGER,
                                                                role_panel_channel_id INTEGER,
                                                                level_up_channel_id INTEGER,
                                                                counting_channel_id INTEGER)
                     """)
    await db.execute("""INSERT OR IGNORE INTO channels(
                                                        guild_id, faq_channel_id, ticket_panel_channel_id, member_counter_channel_id, ticket_logs_channel_id, welcome_channel_id, role_panel_channel_id, level_up_channel_id, counting_channel_id
                                                        ) 
                                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)   
                     """, (
                            1476359827176423426,
                            1479885296035434680,
                            1479885668908797982,
                            1482366789160669224,
                            1482368473647550636,
                            1479886383664464054,
                            1484579505401102357,
                            1482373723037241425,
                            1482373549204312186
                          ))
    await db.execute("""CREATE TABLE IF NOT EXISTS categories (
                                                                guild_id INTEGER PRIMARY KEY,
                                                                open_tickets_cat_id INTEGER,
                                                                closed_tickets_cat_id INTEGER,
                                                                claimed_tickets_cat_id INTEGER)""")
    await db.execute("""INSERT OR IGNORE INTO categories(
        guild_id, open_tickets_cat_id, closed_tickets_cat_id, claimed_tickets_cat_id
    ) VALUES (?, ?, ?, ?)""", (
                         1476359827176423426,
                         1484271991287578746,
                         1484271823171616989,
                         1484272107734171648
                     ))
    await db.execute("""CREATE TABLE IF NOT EXISTS spam(
                                                            guild_id INTEGER PRIMARY KEY,
                                                            messages_in_a_row INTEGER,
                                                            timewindow INTEGER)""")
    await db.execute("""INSERT OR IGNORE INTO spam(guild_id, messages_in_a_row, timewindow) VALUES (?, ?, ?)""", (1476359827176423426, 10, 7))
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