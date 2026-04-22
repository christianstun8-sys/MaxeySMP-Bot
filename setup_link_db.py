import mysql.connector as mariadb
from mysql.connector.abstracts import MySQLConnectionAbstract as Connection

async def init_linkmc_db(conn: Connection):
    cur = conn.cursor()
    cur.execute("""CREATE DATABASE IF NOT EXISTS link_mc;""")
    conn.commit()

async def init_tables(db: Connection):
    cur = db.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS codes(
                                                            code INTEGER PRIMARY KEY,
                                                            uuid TEXT,
                                                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS links(
                                                        discord_id BIGINT PRIMARY KEY,
                                                        minecraft_id TEXT UNIQUE)""")
    cur.execute("""SET GLOBAL event_scheduler = ON;""")
    cur.execute("""CREATE EVENT IF NOT EXISTS delete_old_codes
                    ON SCHEDULE EVERY 1 MINUTE
                    DO
                        DELETE FROM codes WHERE created_at < NOW() - INTERVAL 5 MINUTE""")
    db.commit()

async def get_linking(conn: Connection, uuid: str = None, discord_id: int = None):
    if not discord_id and not uuid:
        return None

    if discord_id and uuid:
        return None

    if discord_id:
        cur = conn.cursor()
        cur.execute("""SELECT minecraft_id FROM links WHERE discord_id = ?""", (discord_id,))
        return cur.fetchone()

    if uuid:
        cur = conn.cursor()
        cur.execute("""SELECT discord_id FROM links WHERE minecraft_id = ?""", (uuid,))
        return cur.fetchone()

    return None
