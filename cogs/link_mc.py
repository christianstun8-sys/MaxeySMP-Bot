import mysql.connector as mariadb
import discord
from discord import Interaction
from discord.ext import commands
import aiohttp
from setup_config_db import get_channel_config, get_message_config


class AlreadyConnectedView(discord.ui.View):
    def __init__(self, linking_db: mariadb.Connection):
        super().__init__()
        self.linking_db = linking_db

    @discord.ui.button(label="Verbindung trennen", style=discord.ButtonStyle.danger, emoji="⛓️‍💥")
    async def callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        user_id = interaction.user.id
        if self.linking_db is not None:
            self.linking_db.commit()
            cursor = self.linking_db.cursor()
            cursor.execute(f"SELECT * FROM links WHERE discord_id = %s", (user_id,))
            check = cursor.fetchone()
            if check is None:
                return await interaction.edit_original_response(content="❌ Deine Accounts sind bereits getrennt.", embed=None, view=None)

            else:
                cursor.execute("DELETE FROM links WHERE discord_id = %s", (user_id,))
                cursor.close()
                self.linking_db.commit()
                return await interaction.edit_original_response(content="✅ Deine Accounts wurden erfolgreich getrennt. Du kannst nun einen anderen Account verbinden.", embed=None, view=None)
        else:
            return await interaction.edit_original_response(content="❌ Es gab einen unerwarteten Fehler. Bitte kontaktiere den Support.", embed=None, view=None)

class CodeInputModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Minecraft-Account verknüpfen")

        self.code_input = discord.ui.TextInput(label="Code eingeben", style=discord.TextStyle.short, placeholder="z.B. 123456", required=True, max_length=6)
        self.add_item(self.code_input)

    async def on_submit(self, interaction: Interaction):
        value = self.code_input.value.strip()
        conn = interaction.client.linking_db

        try:
            int_value = int(value)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Der eingegebene Code ist keine Zahl. Bitte gib einen 6-stelligen Zahlencode ein.",
                ephemeral=True
            )
        print(f"Eingegebener Code: {int_value}")
        conn.commit()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""SELECT uuid FROM codes WHERE code = %s""", (int_value,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            uuid = result['uuid']
            print(f"DB Ergebnis: {result}")
        else:
            return await interaction.response.send_message("❌ Der eingegebene Code ist nicht gültig. Bitte überprüfe, ob du den richtigen Code eingegeben hast.", ephemeral=True)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    name = data["name"]

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""INSERT INTO links (discord_id, minecraft_id) VALUES (%s, %s)""", (interaction.user.id, uuid))

            print(f"Neuer Link: Discord-ID: {interaction.user.id}, Minecraft-ID: {uuid}")

            cursor.execute("""DELETE FROM codes WHERE code = %s""", (int_value,))
            cursor.close()
            conn.commit()
            embed = discord.Embed(title="🔗✅ Erfolgreich verbunden", description=f"Dein Discord Account wurde erfolgreich mit dem Minecraft Account {name} verbunden!", color=discord.Color.green())
            embed.set_thumbnail(url=f"https://visage.surgeplay.com/face/256/{uuid}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except mariadb.IntegrityError:
            return await interaction.response.send_message(f"❌ Dieser Account ist bereits mit einem Discord Account verlinkt.", ephemeral=True)

class OpenCodeModalButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Code eingeben", custom_id="open_code_modal_button", style=discord.ButtonStyle.primary, emoji="↗️")

    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.linking_db
        db.commit()
        cursor = db.cursor()
        cursor.execute("""SELECT minecraft_id FROM links WHERE discord_id = %s""", (interaction.user.id,))
        uuid = cursor.fetchone()
        cursor.close()

        if not uuid:
            await interaction.response.send_modal(CodeInputModal())

        else:
            await interaction.response.defer()
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid[0]}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        name = data["name"]
                        embed = discord.Embed(title=f"⚠️ Bereits verbunden", color=discord.Color.orange(), description=f"Dein Discord Account ist bereits mit einem Minecraft Account verbunden.\n**__Name:__** {name}\n**__UUID:__** {uuid[0]}\n\nWillst du deine Accounts entkoppeln? Dann klicke unten auf den Button.")
                        embed.set_image(url=f"https://visage.surgeplay.com/full/256/{uuid[0]}")
                        embed.set_thumbnail(url=f"https://visage.surgeplay.com/face/256/{uuid[0]}")

                        await interaction.followup.send(embed=embed, ephemeral=True, view=AlreadyConnectedView(db))


class LinkLayout(discord.ui.LayoutView):
    def __init__(self, desc: str = None):
        super().__init__(timeout=None)

        container = discord.ui.Container()

        tb = discord.ui.MediaGallery()
        tb.add_item(media="https://i.ibb.co/7xbXh0Y7/LINKEN.png")
        container.add_item(tb)
        container.add_item(discord.ui.Separator())

        title=discord.ui.TextDisplay("## 🔗 Minecraft Account verlinken")
        container.add_item(title)
        container.add_item(discord.ui.Separator())

        desc = discord.ui.TextDisplay(desc if desc else "### Verbinde deinen Minecraft Account mit deinem Discord Account!\n"
                                      "**1.** Joine dem Minecraft Server und gebe in den Chat ein: `/link`!\n"
                                      "**2.** Kopiere dir den 6-stelligen Code, der als Antwort gesendet wird! Dieser ist für 5 Minuten gültig.\n"
                                      "**3.** Klicke unter dieser Nachricht auf den Button! Daraufhin öffnet sich ein Formular.\n"
                                      "**4. **Füge den Code hier ein und bestätige! Dein Minecraft Account ist nun verbunden!")
        container.add_item(desc)
        container.add_item(discord.ui.Separator())
        row = discord.ui.ActionRow()
        row.add_item(OpenCodeModalButton())
        container.add_item(row)

        self.add_item(container)

async def linkpanel(bot: commands.Bot, guild: discord.Guild, channel: discord.TextChannel = None):
    db = bot.configdb
    messages = await get_message_config(db, guild.id)
    desc = messages[2] if messages and len(messages) > 1 else None

    if channel is None:
        channel_config = await get_channel_config(bot.configdb, guild.id)
        channel_id = channel_config[9]
        channel = guild.get_channel(channel_id)

    try:
        await channel.send(view=LinkLayout(desc))
    except discord.Forbidden:
        pass

class AddViews(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(LinkLayout())

async def setup(bot: commands.Bot):
    await bot.add_cog(AddViews(bot))
