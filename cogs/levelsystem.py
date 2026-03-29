import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import aiosqlite
import asyncio
from pathlib import Path
from setup_config_db import get_channel_config


class LeaderboardView(discord.ui.View):
    def __init__(self, cog, total_users, interaction, embed_color):
        super().__init__(timeout=180)
        self.cog = cog
        self.total_users = total_users
        self.interaction = interaction
        self.embed_color = embed_color
        self.current_page = 0
        self.users_per_page = 10
        self.max_pages = (total_users + self.users_per_page - 1) // self.users_per_page

        if self.max_pages <= 1:
            self.children[0].disabled = True
            self.children[1].disabled = True
        else:
            self.children[0].disabled = True

    @discord.ui.button(label="← Zurück", style=discord.ButtonStyle.blurple)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("Du kannst nicht mit dem Leaderboard eines anderen interagieren.", ephemeral=True)
        self.current_page -= 1
        await self.update_leaderboard(interaction)


    @discord.ui.button(label="Weiter →", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.interaction.user:
            return await interaction.response.send_message("Du kannst nicht mit dem Leaderboard eines anderen interagieren.", ephemeral=True)
        self.current_page += 1
        await self.update_leaderboard(interaction)

    async def update_leaderboard(self, interaction: discord.Interaction):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.max_pages - 1
        offset = self.current_page * self.users_per_page
        new_embed = await self.cog._create_leaderboard_embed(interaction.guild, offset, self.users_per_page, self.total_users)
        await interaction.response.edit_message(embed=new_embed, view=self)

    async def on_timeout(self):
        try:
            message = await self.interaction.original_response()
            await message.edit(view=None)
        except:
            pass

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_dir = Path(__file__).parent.parent / "databases"
        self.db_name = self.db_dir / 'levels.db'
        self.db = bot.level_db
        self.config_db = bot.configdb

        self.MESSAGE_XP = 1
        self.VOICE_XP_PER_MINUTE = 0.5
        self.MAX_MESSAGES_PER_DAY = 200
        self.MAX_VOICE_MINUTES_PER_DAY = 180
        self.STREAK_XP_BONUS_MULTIPLIER = 10

        self.data_base_path = Path(__file__).parent.parent / "data"
        self.RANK_CARD_BACKGROUND_PATH = self.data_base_path / "rank_card_background.png"
        self.FONT_PATH = self.data_base_path / "arial.ttf"

        self.voice_xp_task.start()

    async def cog_load(self):
        await self.setup_db()

    async def setup_db(self):
        await self.db.execute("""
                              CREATE TABLE IF NOT EXISTS levels (
                                                                    guild_id INTEGER NOT NULL,
                                                                    user_id INTEGER NOT NULL,
                                                                    xp INTEGER DEFAULT 0,
                                                                    level INTEGER DEFAULT 0,
                                                                    daily_messages INTEGER DEFAULT 0,
                                                                    daily_voice_minutes INTEGER DEFAULT 0,
                                                                    last_update_date TEXT,
                                                                    current_streak INTEGER DEFAULT 0,
                                                                    last_streak_date TEXT,
                                                                    PRIMARY KEY (guild_id, user_id)
                              )
                              """)
        await self.db.commit()

    def xp_needed_for_level(self, level):
        return 100 + (level * 50)

    def get_xp_multiplier(self):
        return 2 if datetime.now().weekday() >= 5 else 1

    async def _get_user_data_and_reset_daily_limits(self, guild_id, user_id):
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        async with self.db.execute("""
                                   SELECT xp, level, daily_messages, daily_voice_minutes, last_update_date, current_streak, last_streak_date
                                   FROM levels WHERE guild_id = ? AND user_id = ?
                                   """, (guild_id, user_id)) as cursor:
            row = await cursor.fetchone()

        if not row:
            await self.db.execute("""
                                  INSERT INTO levels (guild_id, user_id, last_update_date, current_streak, last_streak_date)
                                  VALUES (?, ?, ?, 0, ?)
                                  """, (guild_id, user_id, today, yesterday))
            return 0, 0, 0, 0, 0, yesterday

        xp, level, daily_messages, daily_voice_minutes, last_update_date, current_streak, last_streak_date = row
        if last_update_date != today:
            daily_messages, daily_voice_minutes = 0, 0
            await self.db.execute("""
                                  UPDATE levels SET daily_messages = 0, daily_voice_minutes = 0, last_update_date = ?
                                  WHERE guild_id = ? AND user_id = ?
                                  """, (today, guild_id, user_id))

        return xp, level, daily_messages, daily_voice_minutes, current_streak, last_streak_date

    async def send_level_up_message(self, member: discord.Member, new_level: int):
        config = await get_channel_config(self.config_db, member.guild.id)
        levelup_channel_id = config[7]
        if levelup_channel_id is None:
            return
        channel = self.bot.get_channel(levelup_channel_id)
        if channel:
            embed = discord.Embed(
                title="🎉 Levelaufstieg!",
                description=f"{member.mention} ist auf **Level {new_level}** aufgestiegen!",
                color=discord.Color.dark_red()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            try:
                await channel.send(embed=embed)
            except:
                pass

    async def _update_xp_and_counters(self, guild_id, user_id, xp, level, xp_to_add, new_msg_count, new_vc_minutes, new_streak, new_last_streak_date):
        guild = self.bot.get_guild(guild_id)
        member = guild.get_member(user_id) if guild else None

        new_xp = xp + xp_to_add
        new_level = level
        level_up = False

        while new_xp >= self.xp_needed_for_level(new_level):
            new_xp -= self.xp_needed_for_level(new_level)
            new_level += 1
            level_up = True

        today = datetime.now().strftime('%Y-%m-%d')
        await self.db.execute("""
                              UPDATE levels SET xp = ?, level = ?, daily_messages = ?, daily_voice_minutes = ?,
                                                last_update_date = ?, current_streak = ?, last_streak_date = ?
                              WHERE guild_id = ? AND user_id = ?
                              """, (new_xp, new_level, new_msg_count, new_vc_minutes, today, new_streak, new_last_streak_date, guild_id, user_id))

        if level_up and member:
            await self.send_level_up_message(member, new_level)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        guild_id, user_id = message.guild.id, message.author.id
        xp_multiplier = self.get_xp_multiplier()
        xp, level, daily_messages, daily_voice_minutes, current_streak, last_streak_date = await self._get_user_data_and_reset_daily_limits(guild_id, user_id)

        new_streak, new_last_streak_date, streak_bonus = current_streak, last_streak_date, 0

        if daily_messages < self.MAX_MESSAGES_PER_DAY:
            if daily_messages == 0:
                today_date = datetime.now().date()
                yesterday = today_date - timedelta(days=1)

                if last_streak_date:
                    last_streak_dt = datetime.strptime(last_streak_date, '%Y-%m-%d').date()
                else:
                    last_streak_dt = today_date

                if last_streak_dt == yesterday:
                    new_streak += 1
                elif last_streak_dt < yesterday:
                    new_streak = 1

                new_last_streak_date = today_date.strftime('%Y-%m-%d')

                if new_streak > 1:
                    streakembed = discord.Embed(
                        title="🔥 Streak verlängert!",
                        description=f"{message.author.mention} hat jetzt einen **Streak von {new_streak} Tagen**!",
                        color=discord.Color.dark_red()
                    )
                    streakembed.set_thumbnail(url=message.author.display_avatar.url)
                    await message.channel.send(embed=streakembed)

            base_xp = self.MESSAGE_XP * xp_multiplier
            streak_bonus = min(new_streak, 5)  # max +5 XP
            xp_to_add = base_xp + streak_bonus
            await self._update_xp_and_counters(guild_id, user_id, xp, level, xp_to_add, daily_messages + 1, daily_voice_minutes, new_streak, new_last_streak_date)
            await self.db.commit()

    @tasks.loop(minutes=1)
    async def voice_xp_task(self):
        if not self.db or not self.bot.is_ready():
            return

        xp_multiplier = self.get_xp_multiplier()
        for guild in self.bot.guilds:

            for member in guild.members:
                if (
                        member.voice
                        and member.voice.channel
                        and not member.bot
                        and not member.voice.self_mute
                        and not member.voice.self_deaf
                ):
                    xp, level, dm, dvm, streak, lsd = await self._get_user_data_and_reset_daily_limits(guild.id, member.id)
                    if dvm < self.MAX_VOICE_MINUTES_PER_DAY:
                        await self._update_xp_and_counters(guild.id, member.id, xp, level, self.VOICE_XP_PER_MINUTE * xp_multiplier, dm, dvm + 1, streak, lsd)
        await self.db.commit()

    @voice_xp_task.before_loop
    async def before_voice_xp_task(self):
        await self.bot.wait_until_ready()

    async def _create_leaderboard_embed(self, guild, offset, limit, total_users):
        async with self.db.execute("""
                                   SELECT user_id, xp, level FROM levels WHERE guild_id = ?
                                   ORDER BY level DESC, xp DESC LIMIT ? OFFSET ?
                                   """, (guild.id, limit, offset)) as cursor:
            top_users = await cursor.fetchall()

        leaderboard_msg = ""
        for index, (u_id, u_xp, u_lvl) in enumerate(top_users):
            member = guild.get_member(u_id)
            name = member.display_name if member else f"User {u_id}"
            leaderboard_msg += f"**#{offset + index + 1}.** {name} - **Level {u_lvl}** ({u_xp} XP)\n"

        embed = discord.Embed(title="🏆 Server Leaderboard", description=leaderboard_msg or "Keine Daten.", color=discord.Color.dark_red())
        embed.set_footer(text=f"Seite {(offset // limit) + 1}/{(total_users + limit - 1) // limit}")
        return embed

    @discord.app_commands.command(name="leaderboard", description="Zeigt die Leveling-Bestenliste an.")
    async def leaderboard_command(self, interaction: discord.Interaction):
        config = await get_channel_config(self.config_db, interaction.guild.id)
        supposed_ch_id = config[7]
        if supposed_ch_id is None:
            return interaction.response.send_message("❌ Fehler beim Bot. Bitte melde dich beim Support!", ephemeral=True)
        supposed = interaction.guild.get_channel(supposed_ch_id)

        if interaction.channel.id != supposed_ch_id and supposed is not None:
            return await interaction.response.send_message(f"❌ Du darfst hier diesen Befehl nicht ausführen. Bitte sende den Befehl noch einmal in dem Kanal {supposed.mention}.", ephemeral=True)

        await interaction.response.defer()
        async with self.db.execute("SELECT COUNT(*) FROM levels WHERE guild_id = ?", (interaction.guild_id,)) as cursor:
            total = (await cursor.fetchone())[0]

        if total == 0:
            return await interaction.followup.send("Noch keine Daten vorhanden.")

        embed = await self._create_leaderboard_embed(interaction.guild, 0, 10, total)
        await interaction.followup.send(embed=embed, view=LeaderboardView(self, total, interaction, discord.Color.dark_red()))



    @discord.app_commands.command(name="rank", description="Zeigt deinen Level-Fortschritt an.")
    async def rank_command(self, interaction: discord.Interaction, member: discord.Member = None):
        config = await get_channel_config(self.config_db, interaction.guild.id)
        supposed_ch_id = config[7]
        if supposed_ch_id is None:
            return interaction.response.send_message("❌ Fehler beim Bot. Bitte melde dich beim Support!", ephemeral=True)
        supposed = interaction.guild.get_channel(supposed_ch_id)

        if interaction.channel.id != supposed_ch_id and supposed is not None:
            return await interaction.response.send_message(f"❌ Du darfst hier diesen Befehl nicht ausführen. Bitte sende den Befehl noch einmal in dem Kanal {supposed.mention}.", ephemeral=True)
        if member is not None:
            if member.bot:
                return await interaction.response.send_message(f"❌ Der Benutzer {member.mention} ist ein Bot und kann keine XP verdienen.", ephemeral=True)

        await interaction.response.defer()
        user = member or interaction.user
        xp, lvl, dm, dvm, streak, lsd = await self._get_user_data_and_reset_daily_limits(interaction.guild_id, user.id)

        required_xp = self.xp_needed_for_level(lvl)
        progress_percent = int((xp / required_xp) * 100) if required_xp > 0 else 0
        bar_length = 20
        filled = int(bar_length * xp / required_xp)
        bar = "🟩" * filled + "⬛" * (bar_length - filled)

        embed = discord.Embed(
            title=f"📊 Level von {user.display_name}",
            color=discord.Color.dark_red()
        )

        embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name="🏆 Level", value=str(lvl), inline=True)
        embed.add_field(name="✨ XP", value=f"{xp} / {required_xp}", inline=True)
        embed.add_field(name="🔥 Streak", value=f"{streak} Tage", inline=True)

        embed.add_field(
            name="📈 Fortschritt",
            value=f"{bar} {progress_percent}%",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    async def cog_unload(self):
        self.voice_xp_task.cancel()

async def setup(bot):
    await bot.add_cog(Leveling(bot))