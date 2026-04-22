import discord
from discord import ui, SeparatorSpacing
from setup_config_db import get_role_config, get_channel_config
from discord.ext import commands


class RolepanelLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        pingcontainer = ui.Container()
        tn = ui.MediaGallery()
        tn.add_item(media="https://i.ibb.co/20fnCWzF/ROLLEN.png")
        pingcontainer.add_item(tn)
        pingcontainer.add_item(ui.Separator())

        desc = ui.TextDisplay("## 🔔 Ping-Rollen\n"
                              "Wähle unten aus, bei welchen Ereignissen du benachrichtigt werden willst! Ein Klick **fügt die Rolle hinzu** oder **entfernt sie** wieder.")
        pingcontainer.add_item(desc)
        pingcontainer.add_item(ui.Separator(spacing=SeparatorSpacing.large))

        ping_buttons = [
            ("Status", "🟢", "ping_status"),
            ("Changelog", "🗒️", "ping_changelog"),
            ("Ankündigungen", "📣", "ping_announces"),
            ("Regeländerungen", "⚖️", "ping_rulechanges")
        ]
        roles_button_row = ui.ActionRow()
        for i, (label, emoji, c_id) in enumerate(ping_buttons):
            btn = ui.Button(label=label, emoji=emoji, custom_id=c_id, style=discord.ButtonStyle.secondary)

            btn.callback = self.button_callback
            roles_button_row.add_item(btn)

        pingcontainer.add_item(roles_button_row)

        self.add_item(pingcontainer)

    async def button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data['custom_id']
        config = await get_role_config(interaction.client.configdb, interaction.client.id)
        role_ids ={
            "ping_status": config[16],
            "ping_changelog": config[15],
            "ping_announces": config[14],
            "ping_rulechanges": config[13]
        }

        role_id = role_ids.get(custom_id)
        role = interaction.guild.get_role(role_id) or await interaction.guild.fetch_role(role_id)
        if role is None:
            return await interaction.response.send_message("❌ Es wurde bisher keine Rolle konfiguriert. Melde dich bitte beim Team.", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            action = "entfernt"
        elif role not in interaction.user.roles:
            await interaction.user.add_roles(role)
            action = "hinzugefügt"
        else:
            return await interaction.response.send_message("❌ Ein Fehler ist aufgetreten. Bitte melde dich beim Team.", ephemeral=True)

        return await interaction.response.send_message(f"✅ Dir wurde erfolgreich die Ping-Rolle {role.mention} {action}", ephemeral=True)

class RolePanelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(view=RolepanelLayout())

async def send_rule_panel(bot: commands.Bot, guild: discord.Guild, channel: discord.TextChannel = None):
    if channel is None:
        config = await get_channel_config(bot.configdb, guild.id)
        channel_id = config[10]
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)

    try:
        await channel.send(view=RolepanelLayout())
    except discord.Forbidden:
        pass

async def setup(bot: commands.Bot):
    await bot.add_cog(RolePanelCog(bot))