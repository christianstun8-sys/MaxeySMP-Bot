import discord
from discord.ext import commands

async def sync(ctx: commands.Context):
    if not ctx.author.guild_permissions.administrator:
        return

    loading_embed = discord.Embed(
        title="<a:loading:1491055212570607617> Befehle werden synchronisiert, einen Moment bitte...",
        color=discord.Color.light_grey(),
    )
    msg = await ctx.send(embed=loading_embed)

    try:
        synced = await ctx.bot.tree.sync()

        success_embed = discord.Embed(
            title=f"<a:success:1491055241813295244> Erfolgreich {len(synced)} Slash-Befehle synchronisiert!",
            color=discord.Color.green()
        )
        await msg.edit(embed=success_embed, content=ctx.author.mention)

    except Exception as e:

        failed_embed = discord.Embed(
            title=f"<a:failed:1491055273920434307> Fehler beim Synchronisieren der Slash-Befehle: {e}",
            color=discord.Color.red(),
        )
        await msg.edit(embed=failed_embed, content=ctx.author.mention)