import discord
from discord.ext import commands
import time
from setup_warn_db import get_warns, warn_someone
from datetime import timedelta
from setup_config_db import get_role_config

user_timestamps = {}
SPAM_THRESHOLD = 2
TIME_WINDOW = 7

class AntiSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.warns_db
        self.config_db = bot.configdb

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        guild = message.guild
        if guild is None:
            return

        config = await get_role_config(self.config_db, message.guild.id)
        team_role_id = config[7]
        team_role = message.guild.get_role(team_role_id)

        if team_role is None:
            return

        if team_role in message.author.roles:
            return

        user_id = message.author.id
        current_time = time.time()

        if user_id not in user_timestamps:
            user_timestamps[user_id] = []

        user_timestamps[user_id] = [
            ts for ts in user_timestamps[user_id] if current_time - ts <= TIME_WINDOW
        ]

        user_timestamps[user_id].append(current_time)

        if len(user_timestamps[user_id]) > SPAM_THRESHOLD:
            user_timestamps[user_id] = []

            print(f"Nachricht von {message.author} blockiert. Spam-Grenzwert überschritten.")

            try:
                await message.delete()
            except discord.Forbidden:
                print("Konnte die Nachricht nicht löschen. Fehlende Berechtigungen.")
                return

            warn_count = await get_warns(self.db, user_id)

            if warn_count[0] and warn_count[0] > 0:
                duration = timedelta(minutes=1)
                await message.author.timeout(duration, reason=f"Spamming in {message.channel.name}")
                action = "⏱️⚠️ Der Benutzer wurde in den Timeout versetzt."

            else:
                await warn_someone(self.db, user_id)
                action = "⚠️ Dem Benutzer wurde eine einmalige Verwarnung erteilt. Bei erneutem Spamming wird er in einen Timeout versetzt."

            embed = discord.Embed(
                title="<:iconmodhqalert:1486035202156400802> Spam erkannt!",
                description=f"Der User {message.author.mention} hat zu viele Nachrichten auf einmal gesendet!\n\n **<:DiscordSafety:1486035194552127670> Ausgeführte Aktion:**\n{action}",
                color=discord.Color.dark_red()
            )
            embed.set_thumbnail(url=message.author.avatar.url)
            await message.channel.send(embed=embed, content=message.author.mention)

async def setup(bot):
    await bot.add_cog(AntiSpam(bot))