import discord
from discord.ext import commands
import dotenv
import os
import aiosqlite
import roleselection
from setup_warn_db import warn_setup_db

import setup_config_db
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

    async def setup_hook(self):
        self.configdb = await aiosqlite.connect("databases/config.db")
        self.ticketdb = await aiosqlite.connect("databases/tickets.db")
        self.roleconfig = await aiosqlite.connect("databases/roleconfig.db")
        self.level_db = await aiosqlite.connect("databases/levels.db")
        self.warns_db = await aiosqlite.connect("databases/warns.db")
        self.counting_db = await aiosqlite.connect("databases/counting.db")
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

        await setup_config_db.config_setup_db(self.configdb)
        await warn_setup_db(self.warns_db)
        await roleselection.setup_rolepanel(self)

    async def on_ready(self):
        print("------------------------------")
        print(f"Bot eingeloggt als {self.user.name} ({self.user.id}).")
        print("------------------------------")
        print("Bot bereit.")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Spielt auf MaxeySMP"))

bot = MaxeySMPBot()
bot.run(TOKEN)