import discord
from discord.ext import commands
import aiosqlite
from setup_config_db import get_channel_config, get_counting_config
from simpleeval import simple_eval

async def init_db(db: aiosqlite.Connection):
    await db.execute(
        """CREATE TABLE IF NOT EXISTS counting (
                                                   current_count INTEGER,
                                                   last_member_id INTEGER,
                                                server_id INTEGER PRIMARY KEY
           )"""
    )
    await db.execute(
        """CREATE TABLE IF NOT EXISTS stats (
                                                server_id INTEGER,
                                                member_id INTEGER,
                                                highest_count INTEGER,
                                                fails INTEGER,
                                                successes INTEGER,
                                                PRIMARY KEY (server_id, member_id)
           )"""
    )
    await db.commit()


async def get_counting_data(db: aiosqlite.Connection, server_id: int):
    async with db.execute("SELECT current_count, last_member_id, server_id FROM counting WHERE server_id = ?", (server_id,)) as cursor:
        return await cursor.fetchone()


async def continue_count(db: aiosqlite.Connection, server_id: int, count: int, last_member_id: int):
    await db.execute("""INSERT OR REPLACE INTO counting (server_id, current_count, last_member_id) VALUES (?, ?, ?)""", (server_id, count, last_member_id))
    await db.commit()

async def get_stat_data(db: aiosqlite.Connection, server_id: int, member_id: int):
    async with db.execute("SELECT highest_count, fails, successes FROM stats WHERE server_id = ? AND member_id = ?", (server_id, member_id)) as cursor:
        return await cursor.fetchone()

async def save_stats(db: aiosqlite.Connection, user_id: int, server_id: int, success: bool, highest: int = None):
    await db.execute(
        "INSERT OR IGNORE INTO stats (server_id, member_id, highest_count, fails, successes) VALUES (?, ?, 0, 0, 0)",
        (server_id, user_id)
    )

    if success:
        await db.execute("UPDATE stats SET successes = successes + 1 WHERE server_id = ? AND member_id = ?", (server_id, user_id))
    else:
        await db.execute("UPDATE stats SET fails = fails + 1 WHERE server_id = ? AND member_id = ?", (server_id, user_id))

    if highest is not None:
        await db.execute("UPDATE stats SET highest_count = ? WHERE server_id = ? AND member_id = ? AND ? > highest_count", (highest, server_id, user_id, highest))

    await db.commit()

class CountingGame(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_db = bot.configdb

    async def cog_load(self):
        await init_db(db=self.bot.counting_db)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        config = await get_channel_config(self.config_db, message.guild.id)
        counting_channel_id = config[8]

        if message.channel.id == counting_channel_id:
            counting_config = await get_counting_config(self.config_db, message.guild.id)
            calculation = counting_config[1]

            self.db = self.bot.counting_db
            data = await get_counting_data(db=self.db, server_id=message.guild.id)
            current_count, last_member_id = (data[0], data[1]) if data else (0, None)

            content = message.content.strip()
            new_count = None

            if calculation == 1:
                try:
                    result = simple_eval(content)
                    if isinstance(result, (int, float)):
                        new_count = int(result)
                except Exception:
                    return
            else:
                if content.isdigit():
                    new_count = int(content)
                else:
                    return

            reason = None
            if last_member_id == message.author.id:
                reason = "Du kannst nicht zweimal hintereinander zählen."
            elif new_count != current_count + 1:
                reason = "Falsche Zahl."

            if reason is not None:
                embed = discord.Embed(
                    title=f"⛓️‍💥 **{message.author.name}** hat das Zählen bei {current_count} zerstört!",
                    description=f"{reason}\n Die nächste Zahl ist **1**",
                    color=discord.Color.dark_red()
                )
                await message.reply(embed=embed, content=message.author.mention)
                await continue_count(self.db, message.guild.id, 0, None)
                await save_stats(self.db, message.author.id, message.guild.id, False)
            else:
                await message.add_reaction("✅")
                db_count = current_count + 1
                await continue_count(self.db, message.guild.id, db_count, message.author.id)
                await save_stats(self.db, message.author.id, message.guild.id, True, db_count)

class StatCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="counting-stats", description="Zeigt von einem User die Zähl-Statistiken an")
    @discord.app_commands.describe(member="Das Mitglied von dem die Statistiken angezeigt werden sollen.")
    async def countingstatscommand(self, interaction: discord.Interaction, member: discord.Member = None):

        if member is None:
            stat_data = await get_stat_data(db=self.bot.counting_db, server_id=interaction.guild.id, member_id=interaction.user.id)
            target_member = interaction.user
        else:
            stat_data = await get_stat_data(db=self.bot.counting_db, server_id=interaction.guild.id, member_id=member.id)
            target_member = member

        if stat_data is None:
            await interaction.response.send_message(f"❌ Der User {member.mention} hat noch nicht mitgezählt.", ephemeral=True)
            return

        highest = stat_data[0]
        fails = stat_data[1]
        successes = stat_data[2]
        quote = (successes / (successes + fails)) * 100
        final_quote = round(quote, 2)


        embed = discord.Embed(
            title=f"{target_member.display_name}'s Zähl-Statistiken",
            description=f"Hier kannst du die Statistiken des Users {target_member.mention} einsehen.",
            color=discord.Color.dark_red()
        )
        embed.set_thumbnail(url=target_member.avatar.url)
        embed.add_field(name="ℹ️ Erfolgsquote", value=f"{final_quote}%", inline=False)
        embed.add_field(name="✅ Erfolge", value=f"{successes} Nachrichten", inline=False)
        embed.add_field(name="❌ Fehler", value=f"{fails} Nachrichten", inline=False)
        embed.add_field(name="👑 Rekordzahl", value=f"{highest}", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(CountingGame(bot))
    await bot.add_cog(StatCommand(bot))
