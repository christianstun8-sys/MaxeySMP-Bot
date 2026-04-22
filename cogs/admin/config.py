import discord
from discord import Interaction
from discord.ext import commands
from cogs.Tickets import ticketpanel
from setup_config_db import get_spam_config, get_link_db_config, get_syncroles_webserver_config
from cogs.link_mc import linkpanel


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
    "member_id": "Mitglied",
    "builder_id": "Builder",
    "rules_update_ping_id": "Regeln Update-Ping"
}

CHANNEL_MAPPING = {
    "faq_channel_id": "FAQ Panel Kanal",
    "ticket_panel_channel_id": "Ticket Panel Kanal",
    "member_counter_channel_id": "Member Counter Anzeige",
    "ticket_logs_channel_id": "Ticket Logs Kanal",
    "welcome_channel_id": "Willkommensnachrichten-Kanal",
    "level_up_channel_id": "Level-Up Kanal",
    "counting_channel_id": "Counting-Game Kanal",
    "link_panel_channel_id": "Minecraft Link Panel Kanal",
    "rule_panel_channel_id": "Regel Panel Kanal"
}

CATEGORY_MAPPING = {
    "open_tickets_cat_id": "Kategorie offene Tickets",
    "closed_tickets_cat_id": "Kategorie geschlossene Tickets",
    "claimed_tickets_cat_id": "Kategorie geclaimte Tickets"
}

MESSAGE_MAPPING = {
    "welcome_message": "Willkommensnachricht",
    "link_mc_message": "Minecraft Link Panel-Nachricht",
    "ticket_panel_message": "Ticket Panel Nachricht",
    "rules_general": "Generelle Regeln",
    "rules_casino": "Kasinoregeln",
    "rules_other": "Andere Verhaltensregeln",
    "rules_cheating": "Cheatingregeln",
    "rules_bugs": "Bugregeln",
    "rules_pvp": "PvP-Regeln",
    "rules_allowed_mods": "Erlaubte Mods",
    "rules_forbidden_mods": "Verbotene Mods",
    "rules_chat": "Chat-Regeln",
    "rules_vc": "VC-Regeln",
    "rules_trading": "Handelsregeln",
    "rules_accounts": "Accountregeln"
}

class SyncrolesWebserverModal(discord.ui.Modal):
    def __init__(self, current_config):
        super().__init__(title="SyncRoles Webserver")

        c_url = current_config[0] if current_config else None
        c_password = current_config[1] if current_config else None

        self.urlinput = discord.ui.TextInput(
            label="URL des Webservers mit Port",
            style=discord.TextStyle.short,
            placeholder="z.B. http://localhost:8080/syncroles/",
            default=c_url,
        )
        self.add_item(self.urlinput)

        self.pwinput = discord.ui.TextInput(
            label="Passwort des Webservers",
            style=discord.TextStyle.long,
            placeholder="z.B. fe210&d)1%",
            default=c_password
        )
        self.add_item(self.pwinput)

    async def on_submit(self, interaction: discord.Interaction):
        url_input = self.urlinput.value.strip()
        pw_input = self.pwinput.value

        if not url_input.startswith("http://") and not url_input.startswith("https://"):
            return await interaction.response.send_message(f"Deine URL-Eingabe '{url_input}' startet nicht mit `http://` oder `https://`.", ephemeral=True)

        configdb = interaction.client.configdb

        try:
            async with configdb.execute("SELECT url FROM syncroles_webserver") as cursor:
                result = await cursor.fetchone()

                if result:
                    await configdb.execute(
                        "UPDATE syncroles_webserver SET url = ?, password = ?",
                        (url_input, pw_input)
                    )
                    await configdb.commit()
                    await interaction.response.send_message("✅ Die Daten wurden erfolgreich gespeichert.", ephemeral=True)
                else:
                    await configdb.execute(
                        "INSERT INTO syncroles_webserver (url, password) VALUES (?, ?)",
                        (url_input, pw_input,)
                    )

                    await configdb.commit()
                    await interaction.response.send_message("✅ Die Daten wurden erfolgreich gespeichert.", ephemeral=True)
        except Exception as e:
            print(e)
            return await interaction.response.send_message(f"❌ Ein unerwarteter Fehler ist aufgetreten. Bitte kontaktiere das Developerteam. Fehler: {e}", ephemeral=True)


class SyncRolesModalOpenButton(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(style=discord.ButtonStyle.green, label="Modal öffnen", emoji="↗️")
    async def callback(self, interaction: discord.Interaction, button):
        config = await get_syncroles_webserver_config(interaction.client.configdb)
        await interaction.response.send_modal(SyncrolesWebserverModal(config))

async def send_syncrolemodal_message(ctx: commands.Context):
    await ctx.reply("🔧 Klicke unten auf den Button, um das Modal zu öffnen und die Webserver-Zugangsdaten für das Minecraft SyncRole Feature anzupassen!", view=SyncRolesModalOpenButton())

class DatabaseModal(discord.ui.Modal):
    def __init__(self, current_config):
        super().__init__(title="Datenbank für Minecraft-Link")

        c_host = current_config[0] if current_config else None
        c_port = current_config[1] if current_config else None
        c_name = current_config[2] if current_config else None
        c_user = current_config[3] if current_config else None
        c_pw   = current_config[4] if current_config else None

        self.hostinput = discord.ui.TextInput(
            label="Host-IP der DB",
            style=discord.TextStyle.short,
            placeholder="z.B. 127.0.0.1",
            default = c_host
        )
        self.portinput = discord.ui.TextInput(
            label="Port der DB",
            style=discord.TextStyle.short,
            placeholder="z.B. 3306",
            max_length=6,
            default=c_port
        )
        self.nameinput = discord.ui.TextInput(
            label="Name der DB",
            style=discord.TextStyle.short,
            placeholder="z.B. link_mc",
            default=c_name
        )
        self.usernameinput = discord.ui.TextInput(
            label="Username des DB-Users",
            style=discord.TextStyle.short,
            placeholder="z.B. root",
            default=c_user
        )
        self.passwordinput = discord.ui.TextInput(
            label="Password des DB-Users",
            style=discord.TextStyle.short,
            placeholder="z.B. MeinTollesPasswort12345!",
            default=c_pw
        )
        self.add_item(self.hostinput)
        self.add_item(self.portinput)
        self.add_item(self.nameinput)
        self.add_item(self.usernameinput)
        self.add_item(self.passwordinput)

    async def on_submit(self, interaction: Interaction):
        db = interaction.client.configdb

        host = self.hostinput.value
        port = int(self.portinput.value)
        name = self.nameinput.value
        username = self.usernameinput.value
        password = self.passwordinput.value

        try:
            async with db.execute("SELECT 1 FROM link_mc_db") as cursor:
                result = await cursor.fetchone()

            if result:
                await db.execute(
                    "UPDATE link_mc_db SET host = ?, port = ?, db_name = ?, username = ?, password = ?",
                    (host, port, name, username, password)
                )
            else:
                await db.execute(
                    "INSERT INTO link_mc_db (host, port, db_name, username, password) VALUES (?, ?, ?, ?, ?)",
                    (host, port, name, username, password)
                )

            await db.commit()
            await interaction.response.send_message("✅ Die Daten wurden erfolgreich gespeichert.", ephemeral=True)
        except Exception as e:
            return await interaction.response.send_message(f"❌ Ein unerwarteter Fehler ist aufgetreten. Bitte kontaktiere das Developerteam. Fehler: {e}", ephemeral=True)


class DBModalOpenButton(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(style=discord.ButtonStyle.green, label="Modal öffnen", emoji="↗️")
    async def callback(self, interaction: discord.Interaction, button):
        config = await get_link_db_config(interaction.client.configdb)
        await interaction.response.send_modal(DatabaseModal(config))

async def send_dbmodal_message(ctx: commands.Context):
    await ctx.reply("🔧 Klicke unten auf den Button, um das Modal zu öffnen und die Datenbank-Zugangsdaten für das Minecraft Link Feature anzupassen!", view=DBModalOpenButton())

class MessageModal(discord.ui.Modal):
    def __init__(self, db_coloumn, display_name):
        self.db_column = db_coloumn
        self.display_name = display_name
        super().__init__(title="Nachricht anpassen")

        self.messageinput = discord.ui.TextInput(
            label=f"Embednachricht",
            style=discord.TextStyle.paragraph,
            placeholder="Hier Nachricht eingeben, leer lassen für Standard",
            max_length=1000,
            required=False
        )
        self.add_item(self.messageinput)

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.configdb
        message_value = self.messageinput.value

        query = f"UPDATE messages SET {self.db_column} = ? WHERE guild_id = ?"
        await db.execute(query, (message_value, interaction.guild.id))
        await db.commit()
        await interaction.response.send_message(f"✅ Die Nachricht für **{self.display_name}** wurde erfolgreich aktualisiert!", ephemeral= True)

class MessageTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, value=key)
            for key, name in MESSAGE_MAPPING.items()
        ]
        super().__init__(placeholder="Was möchtest du konfigurieren?", options=options)

    async def callback(self, interaction: discord.Interaction):
        column = self.values[0]
        display_name = next(name for key, name in MESSAGE_MAPPING.items() if key == column)

        await interaction.response.send_modal(MessageModal(column, display_name))

async def send_message_config_ui(ctx: commands.Context):
    embed = discord.Embed(
        title="⚙️ Nachrichten-Konfiguration",
        description="Wähle im untenstehenden Menü die Nachricht aus, die du für den Bot definieren möchtest.",
        color=discord.Color.blue()
    )
    view = discord.ui.View()
    view.add_item(MessageTypeSelect())
    await ctx.send(embed=embed, view=view)


class RolePicker(discord.ui.RoleSelect):
    def __init__(self, db_column, display_name):
        self.db_column = db_column
        self.display_name = display_name
        super().__init__(placeholder=f"Wähle die Rolle für {display_name}...", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        db = interaction.client.configdb

        ignore_perms = [
            "sub_id",
            "booster_id"
        ]
        if self.db_column not in ignore_perms:
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

        req_voice_channels = [
            "member_counter_channel_id"
        ]
        if self.db_column not in req_voice_channels:
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

        if self.display_name == "Minecraft Link Panel Kanal":
            await linkpanel(interaction.client, interaction.guild, channel)

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