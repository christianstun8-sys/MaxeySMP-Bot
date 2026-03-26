import discord
from discord.ext import commands
from cogs.Tickets import ticketpanel
from setup_config_db import get_spam_config


def can_manage_role(bot_member: discord.Member, target_role: discord.Role) -> bool:
    if not bot_member.guild_permissions.manage_roles:
        return False

    if bot_member.top_role <= target_role:
        return False

    if target_role.managed:
        return False

    return True

def can_manage_channel(bot_member: discord.Member, target_channel: discord.TextChannel):
    if not bot_member.guild_permissions.manage_channels:
        return False

    if not target_channel.permissions_for(bot_member).manage_messages:
        return False

    if not target_channel.permissions_for(bot_member).send_messages:
        return False

    return True

def can_manage_category(bot_member: discord.Member, target_category: discord.CategoryChannel):
    if not bot_member.guild_permissions.manage_channels:
        return False

    if not target_category.permissions_for(bot_member).manage_channels:
        return False

    if not target_category.permissions_for(bot_member).send_messages:
        return False

    if not target_category.permissions_for(bot_member).manage_messages:
        return False

    return True

ROLE_MAPPING = {
    "administrator_id": "Admin",
    "team_lead_id": "Teamleitung",
    "sr_mod_id": "SR Mod",
    "moderator_id": "Mod",
    "developer_id": "Developer",
    "content_creator_id": "Content Creator",
    "staff_id": "Staff",
    "vip_id": "VIP",
    "sub_id": "SUB",
    "booster_id": "Server Booster",
    "member_id": "Mitglied"
}

CHANNEL_MAPPING = {
    "faq_channel_id": "FAQ Kanal",
    "ticket_panel_channel_id": "Ticket Panel Kanal",
    "member_counter_channel_id": "Member Counter Anzeige",
    "ticket_logs_channel_id": "Ticket Logs Kanal",
    "welcome_channel_id": "Willkommensnachrichten-Kanal",
    "level_up_channel_id": "Level-Up Kanal",
    "counting_channel_id": "Counting-Game Kanal"
}

CATEGORY_MAPPING = {
    "open_tickets_cat_id": "Kategorie offene Tickets",
    "closed_tickets_cat_id": "Kategorie geschlossene Tickets",
    "claimed_tickets_cat_id": "Kategorie geclaimte Tickets"
}

class RolePicker(discord.ui.RoleSelect):
    def __init__(self, db_column, display_name):
        self.db_column = db_column
        self.display_name = display_name
        super().__init__(placeholder=f"Wähle die Rolle für {display_name}...", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        db = interaction.client.configdb

        if not can_manage_role(interaction.guild.me, role):
            return await interaction.response.send_message(
                f"❌ Ich kann {role.mention} nicht verwalten. Prüfe meine Position in der Rollenliste!",
                ephemeral=True
            )

        query = f"UPDATE roles SET {self.db_column} = ? WHERE guild_id = ?"
        await db.execute(query, (role.id, interaction.guild.id))
        await db.commit()

        await interaction.response.send_message(
            f"✅ Die Rolle für **{self.display_name}** wurde auf {role.mention} gesetzt.",
            ephemeral=True
        )

class RoleTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, value=key)
            for key, name in ROLE_MAPPING.items()
        ]
        super().__init__(placeholder="Was möchtest du konfigurieren?", options=options)

    async def callback(self, interaction: discord.Interaction):
        column = self.values[0]
        display_name = next(name for key, name in ROLE_MAPPING.items() if key == column)

        view = discord.ui.View()
        view.add_item(RolePicker(column, display_name))

        await interaction.response.send_message(
            f"Wähle jetzt die Server-Rolle aus, die als **{display_name}** fungieren soll:",
            view=view,
            ephemeral=True
        )

async def send_role_config_ui(ctx: commands.Context):
    embed = discord.Embed(
        title="⚙️ Rollen-Konfiguration",
        description="Wähle im untenstehenden Menü die Rolle aus, die du für den Bot definieren möchtest.",
        color=discord.Color.blue()
    )
    view = discord.ui.View()
    view.add_item(RoleTypeSelect())
    await ctx.send(embed=embed, view=view)


class ChannelPicker(discord.ui.ChannelSelect):
    def __init__(self, db_column, display_name):
        self.db_column = db_column
        self.display_name = display_name
        super().__init__(placeholder=f"Wähle den Kanal für {display_name}...", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):

        channel_id = int(self.values[0].id)
        channel = interaction.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ Bitte wähle einen Textkanal aus!",
                ephemeral=True
            )

        db = interaction.client.configdb

        if not can_manage_channel(interaction.guild.me, channel):
            return await interaction.response.send_message(
                f"❌ Ich kann {channel.mention} nicht verwalten oder keine Nachrichten in {channel.mention} senden. Überprüfe meine Rechte.",
                ephemeral=True
            )

        query = f"UPDATE channels SET {self.db_column} = ? WHERE guild_id = ?"
        await db.execute(query, (channel.id, interaction.guild.id))
        await db.commit()

        await interaction.response.send_message(
            f"✅ Der Kanal für **{self.display_name}** wurde auf {channel.mention} gesetzt.",
            ephemeral=True
        )

        if self.display_name == "Ticket Panel Kanal":
            await ticketpanel(interaction.client, interaction.guild, channel)

class ChannelTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, value=key)
            for key, name in CHANNEL_MAPPING.items()
        ]
        super().__init__(placeholder="Was möchtest du konfigurieren?", options=options)

    async def callback(self, interaction: discord.Interaction):
        column = self.values[0]
        display_name = next(name for key, name in CHANNEL_MAPPING.items() if key == column)

        view = discord.ui.View()
        view.add_item(ChannelPicker(column, display_name))

        await interaction.response.send_message(
            f"Wähle jetzt den Kanal aus, der als **{display_name}** fungieren soll:",
            view=view,
            ephemeral=True
        )

async def send_channel_config_ui(ctx: commands.Context):
    embed = discord.Embed(
        title="⚙️ Kanal-Konfiguration",
        description="Wähle im untenstehenden Menü den Kanal aus, den du für den Bot definieren möchtest.",
        color=discord.Color.blue()
    )
    view = discord.ui.View()
    view.add_item(ChannelTypeSelect())
    await ctx.send(embed=embed, view=view)

class CategoryPicker(discord.ui.Modal):
    def __init__(self, display_name, db_column):
        super().__init__(title=f"Kategorie definieren")
        self.display_name = display_name
        self.db_column = db_column

        self.idfield = discord.ui.TextInput(label="ID der Kategorie", style=discord.TextStyle.short, placeholder="Hier die ID eintragen")
        self.add_item(self.idfield)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.idfield.value.strip()
        if not value.isnumeric():
            return await interaction.response.send_message(
                f"❌ Deine Eingabe {value} ist keine ID. Bitte verwende ausschließlich Nummern.", ephemeral=True
            )
        id = int(value)

        cat = interaction.guild.get_channel(id)
        if cat is None:
            return await interaction.response.send_message(f"❌ Deine Eingabe {id} ist keine ID einer existierenden Kategorie.", ephemeral=True)
        if not isinstance(cat, discord.CategoryChannel):
            return await interaction.response.send_message(f"❌ Deine Eingabe {id} ist keine ID einer Kategorie. Bitte gib eine Kategorien-ID an.", ephemeral=True)

        if not can_manage_category(interaction.guild.me, cat):
            return await interaction.response.send_message(f"❌ Ich kann in der Kategorie keine Kanäle verwalten oder Nachrichten senden. Überprüfe meine Rechte.", ephemeral=True)

        db = interaction.client.configdb
        query = f"UPDATE categories SET {self.db_column} = ? WHERE guild_id = ?"
        await db.execute(query, (cat.id, interaction.guild.id))
        await db.commit()

        await interaction.response.send_message(f"✅ Die Kategorie für {self.display_name} wurde auf die ID {id} gesetzt!", ephemeral=True)

class CategoryTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, value=key)
            for key, name in CATEGORY_MAPPING.items()
        ]
        super().__init__(placeholder="Was möchtest du konfigurieren?", options=options)

    async def callback(self, interaction: discord.Interaction):
        column = self.values[0]
        display_name = next(name for key, name in CATEGORY_MAPPING.items() if key == column)

        view = discord.ui.View()
        view.add_item(ChannelPicker(column, display_name))

        await interaction.response.send_modal(CategoryPicker(display_name, column))

async def send_category_config_ui(ctx: commands.Context):
    embed = discord.Embed(
        title="⚙️ Kategorie-Konfiguration",
        description="Wähle im untenstehenden Menü die Kategorie aus, die du für den Bot definieren möchtest.",
        color=discord.Color.blue()
    )
    view = discord.ui.View()
    view.add_item(CategoryTypeSelect())
    await ctx.send(embed=embed, view=view)

class SpamConfigModal(discord.ui.Modal):
    def __init__(self, current_msg, current_time_window):
        super().__init__(title="AntiSpam-System konfigurieren")

        self.timewindow_input = discord.ui.TextInput(
            label="Zeitfenster der Nachrichten (Sek.)",
            placeholder=current_time_window,
        )

        self.msgs_input = discord.ui.TextInput(
            label="Anzahl Nachrichten im Zeitfenster",
            placeholder=current_msg
        )
        self.add_item(self.timewindow_input)
        self.add_item(self.msgs_input)

    async def on_submit(self, interaction: discord.Interaction):
        value_msg = self.msgs_input.value.strip()
        value_tw = self.timewindow_input.value.strip()
        if not value_msg.isnumeric() or not value_tw.isnumeric():
            return await interaction.response.send_message(f"❌ Die Eingaben sind keine Zahlen. Bitte nutze ausschließlich Zahlen als Angabe.", ephemeral=True)

        msg = int(value_msg)
        tw = int(value_tw)
        db = interaction.client.configdb

        await db.execute("""UPDATE spam SET messages_in_a_row = ?, timewindow = ? WHERE guild_id = ?""", (msg, tw, interaction.guild.id))
        await db.commit()

        await interaction.response.send_message(f"✅ Die Nachrichtenanzahl {msg} und das Zeitfenster von {tw} Sekunden wurden übernommen.", ephemeral=True)

class OpenSpamModal(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180.0)

    @discord.ui.button(label="Modal öffnen", style=discord.ButtonStyle.green, emoji="↗️")
    async def open_modal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = interaction.client.configdb
        config = await get_spam_config(db, interaction.guild.id)
        current_msg = config[1]
        current_time_window = config[2]

        await interaction.response.send_modal(SpamConfigModal(current_msg, current_time_window))

async def send_modal_spam_button(ctx: commands.Context):
    await ctx.reply("🔧 Klicke unten auf den Button, um das Modal zu öffnen und das AntiSpam-Feature anzupassen!", view=OpenSpamModal())