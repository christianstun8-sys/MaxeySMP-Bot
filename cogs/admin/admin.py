from discord.ext import commands
from cogs.admin.config import send_role_config_ui, send_channel_config_ui, send_category_config_ui, send_modal_spam_button, send_message_config_ui, send_dbmodal_message, send_syncrolemodal_message
from cogs.Tickets import ticketpanel
from cogs.link_mc import linkpanel
from roleselection import rolepanel_send, rolepanel_addrole, rolepanel_create, rolepanel_removerole, rolepanel_edit
from cogs.rulepanel import send_rule_panel
from cogs.admin.sync import sync
from cogs.faqpanel import send_faq_panel
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
    @commands.has_permissions(administrator=True)
    async def config_antispam(self, ctx):
        await send_modal_spam_button(ctx)

    @config_group.command(name="messages")
    @commands.has_permissions(administrator=True)
    async def config_messages(self, ctx):
        await send_message_config_ui(ctx)

    @config_group.group(name="servers", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def servers_group(self, ctx):
        await ctx.send("🪛 Befehle: `link-mc-db, syncroles-webserver`")

    @servers_group.command(name="syncroles-webserver")
    @commands.has_permissions(administrator=True)
    async def sync_roles_webserver(self, ctx):
        await send_syncrolemodal_message(ctx)

    @servers_group.command(name="link-mc-db")
    @commands.has_permissions(administrator=True)
    async def database_link_mc_db(self, ctx):
        await send_dbmodal_message(ctx)

    @admin_group.group(name="resend", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def resend_group(self, ctx):
        await ctx.send("🪛 Befehle: `ticket-panel, link-panel, faq-panel, rules-panel`")

    @resend_group.command(name="ticket-panel")
    @commands.has_permissions(administrator=True)
    async def resend_ticket_panel(self, ctx: commands.Context):
        await ticketpanel(ctx.bot, ctx.guild)
        await ctx.reply("✅ Ticket-Panel wurde erfolgreich in den konfigurierten Kanal gesendet. Falls keine Nachricht gesendet wurde, wurde noch kein Kanal konfiguriert.")

    @resend_group.command(name="link-panel")
    @commands.has_permissions(administrator=True)
    async def resend_link_panel(self, ctx: commands.Context):
        await linkpanel(ctx.bot, ctx.guild)
        await ctx.reply("✅ MC-Link-Panel wurde erfolgreich in den konfigurierten Kanal gesendet. Falls keine Nachricht gesendet wurde, wurde noch kein Kanal konfiguriert.")

    @resend_group.command(name="faq-panel")
    @commands.has_permissions(administrator=True)
    async def resend_faq_panel(self, ctx: commands.Context):
        await send_faq_panel(ctx.bot, ctx.guild)
        await ctx.reply("✅ FAQ-Panel wurde erfolgreich in den konfigurierten Kanal gesendet. Falls keine Nachricht gesendet wurde, wurde noch kein Kanal konfiguriert.")

    @resend_group.command(name="rules-panel")
    @commands.has_permissions(administrator=True)
    async def resend_rules_panel(self, ctx: commands.Context):
        await send_rule_panel(ctx.bot, ctx.guild)
        await ctx.reply("✅ Rule-Panel wurde erfolgreich in den konfigurierten Kanal gesendet. Falls keine Nachricht gesendet wurde, wurde noch kein Kanal konfiguriert.")

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