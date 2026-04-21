import discord
from discord.ext import commands
import dotenv
import os
import aiosqlite
import roleselection
from setup_warn_db import warn_setup_db
import mysql.connector
from setup_link_db import init_tables, init_linkmc_db
import setup_config_db

# Markenzeichen höhö bin krass :)
print(r'_________ .__          .__          __  .__                        __      ')
print(r'\_   ___ \|  |_________|__| _______/  |_|__|____    ____   _______/  |_    ')
print(r'/    \  \/|  |  \_  __ \  |/  ___/\   __\  \__  \  /    \ /  ___/\   __\   ')
print(r'\     \___|   Y  \  | \/  |\___ \  |  | |  |/ __ \|   |  \\___ \  |  |     ')
print(r' \______  /___|  /__|  |__/____  > |__| |__(____  /___|  /____  > |__|_____')
print(r'        \/     \/              \/               \/     \/     \/    /_____/')

dotenv.load_dotenv()


# ----- BETA -----
beta = False
# ----------------

if beta:
    TOKEN = os.getenv("DISCORD_BETA_TOKEN")
else:
    TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
intents.members = True
intents.messages = True

if beta:
    prefix = "mdev!"
else:
    prefix = "m!"

class MaxeySMPBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=prefix, help_command=None, intents=intents)
        os.makedirs("cogs", exist_ok=True)
        os.makedirs("databases", exist_ok=True)
        self.configdb = None
        self.ticketdb = None
        self.roleconfig = None
        self.level_db = None
        self.warns_db = None
        self.counting_db = None
        self.mariadb = None
        self.linking_db = None

    async def setup_hook(self):
        self.configdb = await aiosqlite.connect("databases/config.db")
        await setup_config_db.config_setup_db(self.configdb)
        self.mdb_config_tuple = await setup_config_db.get_link_db_config(self.configdb)

        if self.mdb_config_tuple is not None:
            self.mdb_config = {
                'host': str(self.mdb_config_tuple[0]),
                'user': str(self.mdb_config_tuple[3]),
                'password': str(self.mdb_config_tuple[4])
            }

            self.mdb_config_db = {
                'host': str(self.mdb_config_tuple[0]),
                'port': int(self.mdb_config_tuple[1]),
                'user': str(self.mdb_config_tuple[3]),
                'password': str(self.mdb_config_tuple[4]),
                'database': str(self.mdb_config_tuple[2])
            }
        else:
            self.mdb_config = None
            self.mdb_config_db = None

        self.ticketdb = await aiosqlite.connect("databases/tickets.db")
        self.roleconfig = await aiosqlite.connect("databases/roleconfig.db")
        self.level_db = await aiosqlite.connect("databases/levels.db")
        self.warns_db = await aiosqlite.connect("databases/warns.db")
        self.counting_db = await aiosqlite.connect("databases/counting.db")

        await warn_setup_db(self.warns_db)

        await roleselection.setup_rolepanel(self)

        if self.mdb_config_tuple is not None:
            try:
                self.mariadb = mysql.connector.connect(**self.mdb_config)
                self.linking_db = mysql.connector.connect(**self.mdb_config_db)
                self.linking_db.autocommit = True
                print(f"✅ Erfolgreich mit MariaDB-Host {self.mdb_config_db['host']} verbunden.")
                await init_tables(self.linking_db)
            except mysql.connector.OperationalError:
                pass

        done = True
        print("Starte Cogs-Ladevorgang...")

        for filename in os.listdir("cogs"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                except Exception as e:
                    print(f"❌ Fehler beim Laden von Cog '{filename[:-3]}': {e}")
                    done = False

        try:
            await self.load_extension(f"cogs.admin.admin")
        except Exception as e:
            print(f"❌ Fehler beim Laden von Cog '{filename[:-3]}': {e}")
            done = False

        if done:
            print("✅ Alle Cogs geladen!")

        try:
            await self.load_extension('jishaku')
            jsk = self.get_command('jsk')
            if jsk:
                jsk.hidden = True
            print("✅ Jishaku erfolgreich geladen!")
        except Exception as e:
            print(f"Fehler beim Laden von Jishaku: {e}")

        if beta:
            synced = await self.tree.sync()
            print(f"[BETA] Erfolgreich {len(synced)} Slash-Befehle synchronisiert")

        if self.mariadb is not None and self.linking_db is not None:
            try:
                await init_linkmc_db(self.mariadb)
            except mysql.connector.OperationalError:
                pass

    async def on_ready(self):
        print("------------------------------")
        print(f"Bot eingeloggt als {self.user.name} ({self.user.id}).")
        print("------------------------------")
        print("Bot bereit.")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Spielt auf MaxeySMP"))

bot = MaxeySMPBot()
bot.run(TOKEN)