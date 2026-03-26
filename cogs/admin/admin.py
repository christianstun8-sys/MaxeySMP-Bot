from discord.ext import commands
from cogs.admin.config import send_role_config_ui, send_channel_config_ui, send_category_config_ui, send_modal_spam_button
from cogs.Tickets import ticketpanel
from roleselection import rolepanel_send, rolepanel_addrole, rolepanel_create, rolepanel_removerole, rolepanel_edit
from cogs.admin.sync import sync
import discord

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="admin", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def admin_group(self, ctx):
        await ctx.send("🔧 Gruppen: `config, resend, roleselection`")

    @admin_group.group(name="config", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def config_group(self, ctx):
        await ctx.send("🪛 Befehle: `roles, channels, categories, antispam`")

    @config_group.command(name="roles")
    @commands.has_permissions(administrator=True)
    async def config_roles(self, ctx):
        await send_role_config_ui(ctx)

    @config_group.command(name="channels")
    @commands.has_permissions(administrator=True)
    async def config_channels(self, ctx):
        await send_channel_config_ui(ctx)

    @config_group.command(name="categories")
    @commands.has_permissions(administrator=True)
    async def config_categories(self, ctx):
        await send_category_config_ui(ctx)

    @config_group.command(name="antispam")
    async def config_antispam(self, ctx):
        await send_modal_spam_button(ctx)

    @admin_group.group(name="resend", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def resend_group(self, ctx):
        await ctx.send("🪛 Befehle: `ticket-panel`")

    @resend_group.command(name="ticket-panel")
    @commands.has_permissions(administrator=True)
    async def resend_ticket_panel(self, ctx: commands.Context):
        await ticketpanel(ctx.bot, ctx.guild)
        await ctx.reply("✅ Ticket-Panel wurde erfolgreich in den konfigurierten Kanal gesendet.")

    @admin_group.group(name="roleselection", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def roleselection_group(self, ctx):
        await ctx.send("🪛 Befehle: `create <Panelname> <Paneltyp (buttons/dropdown)>, role_add <Panelname> <@Role>, role_remove <Panelname> <@Role>, edit <Panelname>, send <Panelname>`")

    @roleselection_group.command(name="create")
    @commands.has_permissions(administrator=True)
    async def rolepanel_create(self, ctx: commands.Context, panel: str, typ: str):
        if panel is None or typ is None:
            await ctx.reply("❌ Die Felder `<Panelname>` und `<Paneltyp (buttons/dropdown)>` müssen ausgefüllt sein.")
            return

        await rolepanel_create(ctx, panel, typ)

    @roleselection_group.command(name="role_add")
    @commands.has_permissions(administrator=True)
    async def role_add(self, ctx: commands.Context, panel: str, role: discord.Role):
        if panel is None or role is None:
            await ctx.reply("❌ Die Felder `<Panelname>` und `<@Role>` müssen ausgefüllt sein.")
            return

        if not isinstance(role, discord.Role):
            await ctx.reply("❌ Das Feld `<@Role>` ist keine Rollenerwähnung.")
            return

        await rolepanel_addrole(ctx, panel, role)

    @roleselection_group.command(name="role_remove")
    @commands.has_permissions(administrator=True)
    async def rolepanel_remove(self, ctx: commands.Context, panel: str, role: discord.Role):
        if panel is None or role is None:
            await ctx.reply("❌ Die Felder `<Panelname>` und `<@Role>` müssen ausgefüllt sein.")
            return
        if not isinstance(role, discord.Role):
            await ctx.reply("❌ Das Feld `<@Role>` ist keine Rollenerwähnung.")
            return

        await rolepanel_removerole(ctx, panel, role)

    @roleselection_group.command(name="send")
    @commands.has_permissions(administrator=True)
    async def rolepanel_send(self, ctx: commands.Context, panel: str):
        if panel is None:
            await ctx.reply("❌ Das Feld `<Panelname>` muss ausgefüllt sein.")
            return

        await rolepanel_send(ctx, panel)

    @roleselection_group.command(name="edit")
    @commands.has_permissions(administrator=True)
    async def rolepanel_edit(self, ctx: commands.Context, panel: str):
        await rolepanel_edit(ctx, panel)

    @admin_group.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context):
        await sync(ctx)

async def setup(bot):
    await bot.add_cog(Admin(bot))