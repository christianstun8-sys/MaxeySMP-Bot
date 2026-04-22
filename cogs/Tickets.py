from pathlib import Path
import discord
import discord.app_commands
from discord.ext import commands
import aiosqlite
import asyncio
import io
from setup_config_db import get_role_config, get_channel_config, get_category_config, get_message_config
from discord.utils import get


# --- HILFSFUNKTIONEN (angepasst auf übergebene DB) ---

async def get_ticket_data(db: aiosqlite.Connection, channel_id: int):
    async with db.execute("SELECT user_id, status, claimed_by FROM tickets WHERE channel_id = ?", (channel_id,)) as cursor:
        return await cursor.fetchone()

async def create_transcript(channel: discord.TextChannel):
    transcript_text = "-" * 30 + "\n\n"
    transcript_text += f"Transkript für Ticket: {channel.name}\n"
    transcript_text += f"ID: {channel.id}\n\n"

    async for message in channel.history(limit=None, oldest_first=True):
        timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        content = message.content

        if message.embeds:
            for embed in message.embeds:
                embed_info = f"[Embed: {embed.title if embed.title else ''} - {embed.description if embed.description else ''}]"
                content += f"\n{embed_info}"

        transcript_text += f"[{timestamp}] {message.author}: {content}\n"

    return io.BytesIO(transcript_text.encode('utf-8'))

async def log_to_channel(bot, guild, embed, file=None):
    config = await get_channel_config(bot.configdb, guild.id)
    log_channel_id = config[4]
    log_channel = bot.get_channel(log_channel_id)
    if log_channel:
        await log_channel.send(embed=embed, file=file)

async def move_ticket_category(bot: commands.Bot, channel: discord.TextChannel, status: str, claimed_by_id: int = None):
    config = await get_category_config(bot.configdb, channel.guild.id)
    category_id = None
    if status == 'geschlossen':
        category_id = config[2]
    elif status == 'offen':
        if claimed_by_id:
            category_id = config[3]
        else:
            category_id = config[1]

    if category_id:
        category = channel.guild.get_channel(category_id)
        if category and isinstance(category, discord.CategoryChannel):
            await channel.edit(category=category)

class TicketReasonSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f"Allgemeiner Support", description="Allgemeines Anliegen", value="support", emoji="<:supporter:1491055169998291137>"),
            discord.SelectOption(label=f"Bug-Report", description="Fehler melden", value="bug", emoji="<:iconmodhqalert:1491055091715805355>"),
            discord.SelectOption(label=f"Media Bewerbung", description="Bewerbung für den Media-Rang", value="mediabewerbung", emoji="🗂️"),
            discord.SelectOption(label=f"Spieler Melden", description="Jemanden melden", value="report",emoji="<:report:1491055052750717010>"),
            discord.SelectOption(label=f"Admin Tickets", description="Sonstiges", value="andere", emoji="<:support_helper:1491055023004848359>"),
        ]
        super().__init__(placeholder="Wähle den Grund für dein Ticket...", min_values=1, max_values=1, options=options, custom_id="reason_dropdown")

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        view = TicketCreateView(interaction.client.ticketdb)
        await view.create_ticket_callback(interaction, selected)

class TicketReasonView(discord.ui.View):
    def __init__(self, supporter: discord.Emoji, mail: discord.Emoji, report: discord.Emoji, support_helper: discord.Emoji):
        super().__init__(timeout=None)
        self.add_item(TicketReasonSelect())

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, db: aiosqlite.Connection):
        super().__init__(timeout=None)
        self.db = db

    @discord.ui.button(label="✅ Ja, löschen", style=discord.ButtonStyle.red, custom_id="confirm_delete_button")
    async def confirm_delete_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_data = await get_ticket_data(self.db, interaction.channel_id)
        if not ticket_data:
            return await interaction.response.send_message("❌ Dieses Ticket existiert nicht mehr in der Datenbank.", ephemeral=True)

        await interaction.response.send_message("Ticket wird in 5 Sekunden gelöscht...", ephemeral=True)
        channel = interaction.channel
        transcript_file = await create_transcript(channel)
        file = discord.File(transcript_file, filename=f"transcript-{channel.name}.txt")

        log_embed = discord.Embed(
            title="Ticket Gelöscht",
            description=f"Ticket **{channel.name}** wurde von {interaction.user.mention} gelöscht.",
            color=discord.Color.dark_red()
        )

        await asyncio.sleep(5)
        await self.db.execute("DELETE FROM tickets WHERE channel_id = ?", (channel.id,))
        await self.db.commit()

        await log_to_channel(interaction.client, interaction.guild, log_embed, file=file)
        await channel.delete()

    @discord.ui.button(label="❌ Abbrechen", style=discord.ButtonStyle.green, custom_id="cancel_delete_button")
    async def cancel_delete_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="✅ Löschvorgang abgebrochen", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=None)

class ClosedTicketView(discord.ui.View):
    def __init__(self, db: aiosqlite.Connection):
        super().__init__(timeout=None)
        self.db = db

    @discord.ui.button(label="🔓 Wieder öffnen", style=discord.ButtonStyle.green, custom_id="ticket_open_button")
    async def open_ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("⚠️ Du hast nicht die Berechtigung, dieses Ticket zu öffnen!", ephemeral=True)

        channel = interaction.channel
        ticket_data = await get_ticket_data(self.db, channel.id)

        if not ticket_data:
            return await interaction.response.send_message("❌ Fehler: Ticket nicht in der Datenbank gefunden.", ephemeral=True)
        if ticket_data[1] == 'offen':
            return await interaction.response.send_message("⚠️ Dieses Ticket ist bereits geöffnet.", ephemeral=True)

        overwrites_to_update = {}
        for target, permissions in channel.overwrites.items():
            if isinstance(target, (discord.Member, discord.User, discord.Role)) and permissions.read_messages:
                overwrites_to_update[target] = discord.PermissionOverwrite(
                    send_messages=True,
                    read_messages=True,
                    read_message_history=True
                )

        for target, overwrite in overwrites_to_update.items():
            await channel.set_permissions(target, overwrite=overwrite)

        await self.db.execute("UPDATE tickets SET status = ? WHERE channel_id = ?", ('offen', channel.id))
        await self.db.commit()

        await move_ticket_category(interaction.client, channel, 'offen')

        log_embed = discord.Embed(
            title="Ticket Wiedereröffnet",
            description=f"Ticket {channel.mention} wurde von {interaction.user.mention} wieder geöffnet.",
            color=discord.Color.green()
        )
        await log_to_channel(interaction.client, interaction.guild, log_embed)

        embed = discord.Embed(title="🔓 Ticket wieder geöffnet", description=f"{interaction.user.mention} hat das Ticket geöffnet!", color=discord.Color.dark_red())
        await interaction.response.send_message(embed=embed, view=OpenTicketView(self.db))

    @discord.ui.button(label="⛔ Löschen", style=discord.ButtonStyle.red, custom_id="delete_ticket_button")
    async def delete_ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("⚠️ Du hast nicht die Berechtigung, dieses Ticket zu löschen!", ephemeral=True)

        embed = discord.Embed(
            title="❗ Bist du sicher?",
            description="Diese Aktion kann **nicht** rückgängig gemacht werden. Der Channel wird permanent gelöscht.",
            color=discord.Color.dark_red()
        )
        await interaction.response.send_message(embed=embed, view=ConfirmDeleteView(self.db), ephemeral=True)

class OpenTicketView(discord.ui.View):
    def __init__(self, db: aiosqlite.Connection):
        super().__init__(timeout=None)
        self.db = db

    @discord.ui.button(label="🔒 Schließen", style=discord.ButtonStyle.red, custom_id="ticket_close_button")
    async def close_ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.followup.send("⚠️ Du hast nicht die Berechtigung, dieses Ticket zu schließen.", ephemeral=True)

        channel = interaction.channel
        ticket_data = await get_ticket_data(self.db, channel.id)

        if not ticket_data:
            return await interaction.followup.send("❌ Fehler: Ticket nicht in der Datenbank gefunden.", ephemeral=True)
        if ticket_data[1] == 'geschlossen':
            return await interaction.followup.send("⚠️ Dieses Ticket ist bereits geschlossen.", ephemeral=True)

        config = await get_role_config(interaction.client.configdb, interaction.guild_id)
        if not config:
            return await interaction.response.send_message("❌ Fehler: Konfiguration für diesen Server nicht gefunden.", ephemeral=True)

        reason = None
        async with self.db.execute("SELECT reason FROM tickets WHERE channel_id = ?", (channel.id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                reason = row[0]

        role_mapping = {
            "support": [config[1], config[2]],
            "bug": [config[5], config[1], config[2]],
            "mediabewerbung": [config[3]],
            "report": [config[1], config[2]],
            "andere": [config[5], config[1], config[2]]
        }

        allowed_roles = role_mapping.get(reason, [])

        overwrites_to_update = {}
        for target, permissions in channel.overwrites.items():
            is_allowed_role = isinstance(target, discord.Role) and target.id in allowed_roles
            is_bot = target.id == interaction.guild.me.id

            if not is_allowed_role and not is_bot and permissions.send_messages:
                overwrites_to_update[target] = discord.PermissionOverwrite(
                    send_messages=False,
                    read_messages=True,
                    read_message_history=True
                )
        user_id = ticket_data[0]
        member = interaction.guild.get_member(user_id)
        if member and member not in overwrites_to_update:
            overwrites_to_update[member] = discord.PermissionOverwrite(
                send_messages=False,
                read_messages=True,
                read_message_history=True
            )

        for target, overwrite in overwrites_to_update.items():
            await channel.set_permissions(target, overwrite=overwrite)

        await self.db.execute("UPDATE tickets SET status = ?, claimed_by = NULL WHERE channel_id = ?", ('geschlossen', channel.id))
        await self.db.commit()

        await move_ticket_category(interaction.client, channel, 'geschlossen')

        log_embed = discord.Embed(
            title="Ticket Geschlossen",
            description=f"Ticket {channel.mention} wurde von {interaction.user.mention} geschlossen.",
            color=discord.Color.orange()
        )
        await log_to_channel(interaction.client, interaction.guild, log_embed)

        embed = discord.Embed(
            title="🔒 Ticket geschlossen",
            description=f"{interaction.user.mention} hat das Ticket geschlossen.",
            color=discord.Color.dark_red()
        )
        await interaction.followup.send(embed=embed, view=ClosedTicketView(self.db))

class TicketClaimView(discord.ui.View):
    def __init__(self, db: aiosqlite.Connection):
        super().__init__(timeout=None)
        self.db = db

    @discord.ui.button(label="👍 Claim", style=discord.ButtonStyle.secondary, custom_id="ticket_claim_button")
    async def claim_ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("⚠️ Du hast nicht die Berechtigung, dieses Ticket zu claimen.", ephemeral=True)

        ticket_data = await get_ticket_data(self.db, interaction.channel.id)
        if not ticket_data:
            return await interaction.response.send_message("❌ Fehler: Ticket nicht in der Datenbank gefunden.", ephemeral=True)

        if ticket_data[1] != 'offen':
            return await interaction.response.send_message("⚠️ Nur offene Tickets können geclaimt werden.", ephemeral=True)

        claimed_by_id = ticket_data[2]
        new_claimed_by_id = None

        if claimed_by_id is None:
            new_claimed_by_id = interaction.user.id
            await self.db.execute("UPDATE tickets SET claimed_by = ? WHERE channel_id = ?", (new_claimed_by_id, interaction.channel.id))
            embed = discord.Embed(description=f"{interaction.user.mention} hat dieses Ticket geclaimt.", color=discord.Color.dark_red())
            await move_ticket_category(interaction.client, interaction.channel, 'offen', claimed_by_id=new_claimed_by_id)

            log_embed = discord.Embed(
                title="Ticket Geclaimt",
                description=f"Ticket {interaction.channel.mention} wurde von {interaction.user.mention} geclaimt.",
                color=discord.Color.blue()
            )
            await log_to_channel(interaction.client, interaction.guild, log_embed)

        elif claimed_by_id == interaction.user.id:
            await self.db.execute("UPDATE tickets SET claimed_by = NULL WHERE channel_id = ?", (interaction.channel.id,))
            embed = discord.Embed(description=f"{interaction.user.mention} hat den Claim für dieses Ticket entfernt.", color=discord.Color.dark_red())
            await move_ticket_category(interaction.client, interaction.channel, 'offen', claimed_by_id=None)

            log_embed = discord.Embed(
                title="Ticket Unclaimed",
                description=f"{interaction.user.mention} hat den Claim für {interaction.channel.mention} aufgehoben.",
                color=discord.Color.light_grey()
            )
            await log_to_channel(interaction.client, interaction.guild, log_embed)

        else:
            claimer = interaction.guild.get_member(claimed_by_id)
            return await interaction.response.send_message(f"Dieses Ticket ist bereits von {claimer.mention if claimer else 'einem Teammitglied'} geclaimt.", ephemeral=True)

        await self.db.commit()
        await interaction.response.send_message(embed=embed)

class TicketCreateView(discord.ui.View):
    def __init__(self, db: aiosqlite.Connection):
        super().__init__(timeout=None)
        self.db = db

    async def create_ticket_callback(self, interaction: discord.Interaction, reason: str):
        await interaction.response.defer(ephemeral=True)

        role_config = await get_role_config(interaction.client.configdb, interaction.guild.id)
        cat_config = await get_category_config(interaction.client.configdb, interaction.guild.id)
        if not role_config or not cat_config:
            return await interaction.followup.send("Fehler: Konfiguration für diesen Server nicht gefunden.", ephemeral=True)

        async with self.db.execute("SELECT channel_id FROM tickets WHERE user_id = ? AND status = ?", (interaction.user.id, 'offen')) as cursor:
            existing_ticket = await cursor.fetchone()

        if existing_ticket:
            return await interaction.followup.send(f"Du hast bereits ein offenes Ticket: <#{existing_ticket[0]}>", ephemeral=True)

        guild = interaction.guild
        category = guild.get_channel(cat_config[1])
        if not category:
            return await interaction.followup.send("Fehler: Die Kategorie für offene Tickets wurde nicht gefunden.", ephemeral=True)

        op = interaction.user
        role_mapping = {
            "support": [role_config[1], role_config[2]],
            "bug": [role_config[5], role_config[1], role_config[2]],
            "mediabewerbung": [role_config[3]],
            "report": [role_config[1], role_config[2]],
            "andere": [role_config[5], role_config[1], role_config[2]]
        }

        allowed_roles = role_mapping.get(reason, [])

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            op: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        for role_id in allowed_roles:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    view_channel=True
                )

        safe_name = interaction.user.name.lower().replace(" ", "-")[:20]
        channel_name = f"ticket-{safe_name}"
        new_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites, category=category)

        await self.db.execute(
            "INSERT INTO tickets (channel_id, user_id, status, reason) VALUES (?, ?, ?, ?)",
            (new_channel.id, interaction.user.id, 'offen', reason)
        )
        await self.db.commit()

        reason_title_mapping = {
            "support": "<:supporter:1491055169998291137> Allgemeiner Support",
            "bug": "<:iconmodhqalert:1491055091715805355> Bug-Report",
            "mediabewerbung": "🗂️ Media-Bewerbungen",
            "report": "<:report:1491055052750717010> Report-Support",
            "andere": "<:support_helper:1491055023004848359> Andere Anlässe"
        }

        reason_description_mapping = {
            "support": "Willkommen im **Allgemeinem Support**, beschreibe uns dein Anliegen deine Frage o.ä. bitte genaustens!\n"
                       "Wir wollen mitteilen, dass Trolling usw. **im schlimmsten Fall** zu einem Ban führen kann! ⚠️ \n\n"
                       "Bitte habe Verständnis, dass die Moderatoren ein wenig Zeit brauchen um zu antworten. Außerdem bitten wir dich das Pingen der Teammitglieder zu unterlassen. \n\n"
                       "Liebe Grüße,\n"
                       "Dein Maxey-SMP Team <:MaxeyAxolotlLove:1491054981602611321>",
            "bug": "Willkommen im **Bug-Report Ticket**, beschreibe uns dein Bug deine Fehlermeldung o.ä. bitte genaustens! Wir empfehlen immer, Videos, Bilder usw. anzufügen. \n\n"
                   "Wir wollen mitteilen, dass Trolling usw. **im schlimmsten Fall** zu einem Ban führen kann! ⚠️ \n\n"
                   "Bitte habe Verständnis, dass die Moderatoren ein wenig Zeit brauchen um zu antworten. Außerdem bitten wir dich, das Pingen der Teammitglieder zu unterlassen. \n\n"
                   "Liebe Grüße,\nDein Maxey-SMP Team <:MaxeyAxolotlLove:1491054981602611321>",
            "mediabewerbung": "Willkommen bei den Team-Bewerbungen! Bitte gib uns als ersten Schritt ein paar Eck-Informationen von dir:\n\n"
                             "- Name & Alter\n"
                             "- Welche Position (Discord Mod, Ingame Mod, Dev, usw.)\n"
                             "- Deine Erfahrung und wo du sie gesammelt hast\n"
                             "- Warum wir genau dich nehmen sollten (Was kannst du, was andere vielleicht nicht haben)\n\n"
                             "Wir wollen mitteilen, dass Trolling usw. im schlimmsten Fall zu einem Ban führen kann! ⚠️ \n\n"
                             "Bitte habe Verständnis, dass die Teamleitung ein wenig Zeit braucht um zu antworten. Außerdem bitten wir dich, das Pingen der Teammitglieder zu unterlassen.\n"
                             "Liebe Grüße,\nDein Maxey-SMP Team <:MaxeyAxolotlLove:1491054981602611321>",
            "report": "Willkommen im Report-Support! Wenn du einen Spieler Ingame oder eine Person auf diesem Discord Server melden möchtest, beschreibe uns das Problem genaustens!\n"
                      "Wir empfehlen Videos, Bilder usw. immer anzufügen.\n\n"
                      "Wir wollen mitteilen, dass Trolling von dem Ticketersteller und anderen zu einem Ban führen kann! ⚠️ \n\n"
                      "Bitte habe Verständnis, dass die Teamleitung ein wenig Zeit braucht um zu antworten. Außerdem bitten wir dich, das Pingen der Teammitglieder zu unterlassen.\n\n"
                      "Liebe Grüße,\n\nDein Maxey-SMP Team <:MaxeyAxolotlLove:1491054981602611321>",
            "andere": "Hallo! Hast du einen ganz anderen Anlass und die anderen Kategorien haben nicht mit deinem Ticketeröffnungsgrund übereingestimmt?\n"
                      "Dann bist du hier genau richtig! Beschreibe uns deinen Anlass bitte genaustens. \n\n"
                      "Wir wollen mitteilen, dass Trolling von dem Ticketersteller usw. zu einem Ban führen kann! ⚠️ \n\n"
                      "Bitte habe Verständnis, dass die Teamleitung ein wenig Zeit braucht um zu antworten. Außerdem bitten wir dich, das Pingen der Teammitglieder zu unterlassen. \n\n"
                      "Liebe Grüße,\nDein Maxey-SMP Team <:MaxeyAxolotlLove:1491054981602611321>"
        }

        title=reason_title_mapping[reason]
        desc=reason_description_mapping[reason]

        embed = discord.Embed(
            title=title,
            description=desc,
            color=discord.Color.dark_red()
        )

        log_embed = discord.Embed(
            title="Neues Ticket!",
            description=f"{interaction.user.mention} ({interaction.user.id}) hat ein neues Ticket erstellt: {new_channel.mention}",
            color=discord.Color.dark_red()
        )

        await new_channel.send(embed=embed, view=OpenTicketView(self.db), content=f"{interaction.user.mention}")
        await new_channel.send(view=TicketClaimView(self.db))
        await interaction.followup.send(f"Dein Ticket wurde erstellt: {new_channel.mention}", ephemeral=True)
        await log_to_channel(interaction.client, interaction.guild, log_embed)

# --- COGS ---

class TicketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.ticketdb

    async def cog_load(self):
        dd_supporter = self.bot.get_emoji(1484520957908353146)
        dd_mail = self.bot.get_emoji(1484521006604484690)
        dd_supporthelper = self.bot.get_emoji(1484521071918059701)
        dd_report = self.bot.get_emoji(1484521040645324800)
        await self.init_db()
        self.bot.add_view(TicketCreateView(self.db))
        self.bot.add_view(OpenTicketView(self.db))
        self.bot.add_view(ClosedTicketView(self.db))
        self.bot.add_view(ConfirmDeleteView(self.db))
        self.bot.add_view(TicketClaimView(self.db))
        self.bot.add_view(TicketReasonView(dd_supporter, dd_mail, dd_report, dd_supporthelper))

    async def init_db(self):
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                                                channel_id INTEGER PRIMARY KEY,
                                                user_id INTEGER NOT NULL,
                                                status TEXT NOT NULL,
                                                claimed_by INTEGER,
                                                reason TEXT
            )
            """
        )
        await self.db.commit()

class AddMember(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.ticketdb

    @discord.app_commands.command(name="ticket-addmember", description="Fügt einen Benutzer zum aktuellen Ticket hinzu.")
    @discord.app_commands.checks.has_permissions(manage_messages=True)
    async def ticket_add_member(self, interaction: discord.Interaction, member: discord.Member):
        channel = interaction.channel
        ticket_data = await get_ticket_data(self.db, channel.id)
        if not ticket_data:
            return await interaction.response.send_message("❌ Dieser Befehl kann nur in einem registrierten Ticket-Kanal verwendet werden.", ephemeral=True)

        overwrites = channel.overwrites_for(member)
        overwrites.read_messages = True
        overwrites.send_messages = True

        await channel.set_permissions(member, overwrite=overwrites)
        await interaction.response.send_message(f"{member.mention} wurde dem Ticket erfolgreich hinzugefügt.")

        log_embed = discord.Embed(
            title="Mitglied Hinzugefügt",
            description=f"{interaction.user.mention} hat {member.mention} zum Ticket {channel.mention} hinzugefügt.",
            color=discord.Color.blue()
        )
        await log_to_channel(self.bot, interaction.guild, log_embed)


class RemoveMember(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.ticketdb

    @discord.app_commands.command(name="ticket-removemember", description="Entfernt einen Nutzer aus dem aktuellen Ticket.")
    @discord.app_commands.checks.has_permissions(manage_messages=True)
    async def ticket_remove_member(self, interaction: discord.Interaction, member: discord.Member):
        channel = interaction.channel
        ticket_data = await get_ticket_data(self.db, channel.id)
        if not ticket_data:
            return await interaction.response.send_message("❌ Dieser Befehl kann nur in einem registrierten Ticket-Kanal verwendet werden.", ephemeral=True)

        overwrites = channel.overwrites_for(member)
        overwrites.read_messages = False
        overwrites.send_messages = False

        await channel.set_permissions(member, overwrite=overwrites)
        await interaction.response.send_message(f"{member.mention} wurde vom Ticket erfolgreich entfernt.")

        log_embed = discord.Embed(
            title="Mitglied Entfernt",
            description=f"{interaction.user.mention} hat {member.mention} aus dem Ticket {channel.mention} entfernt.",
            color=discord.Color.blue()
        )
        await log_to_channel(self.bot, interaction.guild, log_embed)

async def setup(bot):
    await bot.add_cog(TicketCog(bot))
    await bot.add_cog(AddMember(bot))
    await bot.add_cog(RemoveMember(bot))

class TicketLayout(discord.ui.LayoutView):
    def __init__(self, desc: str = None):
        super().__init__(timeout=None)

        container = discord.ui.Container()

        img = discord.ui.MediaGallery()
        img.add_item(media="https://i.ibb.co/ZRtdZPhm/TICKETS.png")
        container.add_item(img)
        container.add_item(discord.ui.Separator())

        title = discord.ui.TextDisplay("## <:supporter:1491055169998291137> Ticket-Support")
        container.add_item(title)
        container.add_item(discord.ui.Separator())

        desc = discord.ui.TextDisplay(desc if desc else "Bitte wähle ein Anliegen aus, um ein Ticket zu erstellen!\n\n"
                                                        "<:mail:1491055135554670842> **Allgemeiner Support:**\n"
                                                        "Bitte öffne dieses Ticket, wenn du allgemeine Anliegen, Fragen oder Anfragen hast!\n\n"
                                                        "<:iconmodhqalert:1491055091715805355> **Bug-Report:**\n"
                                                        "Bitte öffne dieses Ticket, wenn du einen bestimmten Bug auf dem Discord Server **oder auch** Ingame gefunden hast!\n"
                                                        "Wir bitten darum, den Bug genaustens zu beschreiben und, wenn möglich, Anhänge (zB. Bilder, Videos) als Anhang anzuhängen.\n\n"
                                                        "🗂️ **Media Bewerbung:**\n"
                                                        "Um den Media-Rang zu erhalten, muss mindestens eine der folgenden Anforderungen erfüllt sein: \n"
                                                        "- Mindestens 20 durchschnittliche Zuschauer im Stream\n"
                                                        "- Mindestens 80 durchschnittliche Zuschauer bei TikTok-Streams\n"
                                                        "- Mindestens 3.000 Aufrufe auf einem YouTube-Video\n"
                                                        "- Mindestens 50.000 Aufrufe auf TikTok, YouTube Shorts oder Instagram Reels\n"
                                                        "Hast du diese Aufrufe erreicht? Öffne ein Ticket, um deinen Rang zu erhalten!\n\n"
                                                        "<:report:1491055052750717010> **Spieler Report:**\n"
                                                        "Wenn ihr einen User auf diesem Ingame oder auch auf diesem Discord reporten wollt, öffnet bitte dieses Ticket. \n\n"
                                                        "<:support_helper:1491055023004848359> **Admin Ticket:**\n"
                                                        "Hier kannst du dich bei uns melden, wenn du ein Anliegen hast, das direkt das Admin-Team betrifft. Dazu gehören z.B. spezielle Anfragen, Probleme, Mod Abuse, Beschwerden oder andere wichtige Themen, die nicht in andere Ticket-Kategorien passen.\n\n\n"
                                                        "Euer MaxeyTV-SMP Team <:MaxeyAxolotlLove:1491054981602611321>")
        container.add_item(desc)
        container.add_item(discord.ui.Separator())
        row = discord.ui.ActionRow()
        row.add_item(TicketReasonSelect())
        container.add_item(row)

        self.add_item(container)
    
async def ticketpanel(bot: commands.Bot, guild, channel: discord.TextChannel = None):
    db = bot.configdb
    messages = await get_message_config(db, guild.id)
    desc = messages[3] if messages and len(messages) > 1 else None

    if channel is None:
        channel_config = await get_channel_config(bot.configdb, guild.id)
        channel_id = channel_config[2]
        channel = guild.get_channel(channel_id)
    try:
        await channel.send(view=TicketLayout(desc))
    except discord.Forbidden:
        pass