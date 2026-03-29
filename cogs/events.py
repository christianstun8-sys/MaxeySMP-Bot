import discord
from discord.ext import commands
from setup_config_db import get_channel_config, get_role_config
from discord.utils import get

class WelcomeMessages(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        config = await get_channel_config(self.bot.configdb, member.guild.id)
        ruleschannel = member.guild.get_channel(1476362373819273366)
        ingamerules = member.guild.get_channel(1482712289176981616)
        tickets = member.guild.get_channel(1479885668908797982)
        welcomeembed = discord.Embed(
            title=f"Willkommen auf dem offiziellen MaxeyTV-SMP Server!",
            description=f"Hey und schön, dass du da bist!\n"
                        f"Wir freuen uns riesig, dich in unserer SMP-Community begrüßen zu dürfen. <:MaxeyAxolotlHi:1486035188621508728>\n"
                        f"Bevor du loslegst, nimm dir bitte kurz Zeit und lies dir unser Server-Regelwerk {ruleschannel.mention} sowie das Ingame-Regelwerk {ingamerules.mention} sorgfältig durch. <:rules:1486035195772665938>\n"
                        f"Das hilft uns allen, eine faire, entspannte und spaßige Umgebung zu schaffen. <:DiscordSafety:1486035194552127670>\n\n"
                        f""
                        f"Wenn du Fragen hast, kannst du dich jederzeit an das Team beim {tickets.mention} wenden – wir helfen dir gerne weiter! <:SupporterOnDuty:1486035192404643870>\n"
                        f"Jetzt wünschen wir dir ganz viel Spaß auf dem Server und eine tolle Zeit mit der Community! \n\n"
                        f""
                        f"Dein MaxeyTV-SMP Team <:MaxeyAxolotlLovePink:1486035190248767498>!",
            color=discord.Color.dark_blue()
        )
        welcomeembed.set_thumbnail(member.guild.icon.url)

        welcomechannel = member.guild.get_channel(config[5])
        await welcomechannel.send(embed=welcomeembed, content=member.mention)

class JoinRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        config = await get_role_config(self.bot.configdb, member.guild.id)
        member_role = await member.guild.get_role(config[11])
        try:
            if not member_role in member.roles:
                await member.add_roles(member_role)

        except discord.Forbidden:
            print(f"[DISCORD.FORBIDDEN]: Keine Berechtigung, {member.display_name} die Member-Rolle zuzuweisen.")

class Membercounter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        count = sum(1 for member in member.guild.members if not member.bot)

        config = await get_channel_config(self.bot.configdb, member.guild.id)
        member_count_channel = member.guild.get_channel(config[3])
        await member_count_channel.edit(name=f"👥・Members: {count}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        count = sum(1 for member in member.guild.members if not member.bot)

        config = await get_channel_config(self.bot.configdb, member.guild.id)
        member_count_channel = member.guild.get_channel(config[3])
        await member_count_channel.edit(name=f"👥・Members: {count}")

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(1476359827176423426)
        count = sum(1 for member in guild.members if not member.bot)

        config = await get_channel_config(self.bot.configdb, guild.id)
        member_count_channel = guild.get_channel(config[3])
        if member_count_channel is not None:
            await member_count_channel.edit(name=f"👥・Members: {count}")


async def setup(bot):
    await bot.add_cog(JoinRole(bot))
    await bot.add_cog(WelcomeMessages(bot))
    await bot.add_cog(Membercounter(bot))



