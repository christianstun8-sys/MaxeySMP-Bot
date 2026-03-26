import aiosqlite
import discord
from discord.ext import commands
from setup_config_db import get_channel_config

# =========================
# VIEW
# =========================

class RolePanelView(discord.ui.View):
    def __init__(self, panel, roles):
        super().__init__(timeout=None)
        self.panel = panel
        self.roles = roles

        if self.panel["type"] == "buttons":
            for r in self.roles:
                btn = discord.ui.Button(
                    label=r["label"],
                    emoji=r["emoji"] or None,
                    style=discord.ButtonStyle(r["style"]),
                    custom_id=f"role_{r['role_id']}"
                )
                btn.callback = self.button_callback
                self.add_item(btn)
        else:
            options = [
                discord.SelectOption(
                    label=r["label"],
                    value=str(r["role_id"]),
                    emoji=r["emoji"] or None
                ) for r in self.roles
            ]

            select = discord.ui.Select(
                placeholder="Wähle deine Rollen...",
                options=options,
                min_values=0,
                max_values=len(options),
                custom_id=f"select_{self.panel['name']}"
            )
            select.callback = self.select_callback
            self.add_item(select)

    async def button_callback(self, interaction: discord.Interaction):
        role_id = int(interaction.data["custom_id"].split("_")[1])
        role = interaction.guild.get_role(role_id)

        if not role:
            return await interaction.response.send_message("❌ Rolle nicht gefunden.", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"➖ {role.name} entfernt", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"➕ {role.name} hinzugefügt", ephemeral=True)

    async def select_callback(self, interaction: discord.Interaction):
        selected = [int(v) for v in interaction.data.get("values", [])]

        guild = interaction.guild
        user = interaction.user

        for r in self.roles:
            role = guild.get_role(r["role_id"])
            if not role:
                continue

            if r["role_id"] in selected and role not in user.roles:
                await user.add_roles(role)
            elif r["role_id"] not in selected and role in user.roles:
                await user.remove_roles(role)

        await interaction.response.send_message("✅ Rollen aktualisiert.", ephemeral=True)


# =========================
# SETUP FUNCTION
# =========================

class RolePanelEditModal(discord.ui.Modal, title="Panel bearbeiten"):
    def __init__(self, panel_name, db):
        super().__init__()
        self.panel_name = panel_name
        self.db = db

        self.title_input = discord.ui.TextInput(
            label="Titel",
            required=False,
            max_length=100
        )

        self.description_input = discord.ui.TextInput(
            label="Beschreibung (| = Zeilenumbruch)",
            style=discord.TextStyle.paragraph,
            required=False
        )

        self.footer_input = discord.ui.TextInput(
            label="Footer",
            required=False,
            max_length=100
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.footer_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.db.execute(
            "UPDATE panels SET title = ?, description = ?, footer = ? WHERE name = ?",
            (
                self.title_input.value,
                self.description_input.value,
                self.footer_input.value,
                self.panel_name
            )
        )
        await self.db.commit()

        await interaction.response.send_message(
            f"✅ Panel `{self.panel_name}` wurde aktualisiert.",
            ephemeral=True
        )

class EditModalButton(discord.ui.View):
    def __init__(self, panel: str, db: aiosqlite.Connection):
        super().__init__(timeout=180.0)
        self.panel = panel
        self.db = db

    @discord.ui.button(label="Modal öffnen", style=discord.ButtonStyle.green, emoji="↗️")
    async def openbutton(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RolePanelEditModal(panel_name=self.panel, db=self.db))


async def setup_rolepanel(bot: commands.Bot):
    db = bot.roleconfig
    await db.execute("""
                     CREATE TABLE IF NOT EXISTS panels (
                                                           name TEXT PRIMARY KEY,
                                                           title TEXT,
                                                           description TEXT,
                                                           footer TEXT,
                                                           type TEXT,
                                                           channel_id INTEGER,
                                                           message_id INTEGER
                     )
                     """)

    await db.execute("""
                     CREATE TABLE IF NOT EXISTS panel_roles (
                                                                panel_name TEXT,
                                                                role_id INTEGER,
                                                                label TEXT,
                                                                emoji TEXT,
                                                                style INTEGER,
                                                                PRIMARY KEY(panel_name, role_id)
                     )
                     """)

    await db.commit()

    db = bot.roleconfig
    async with db.execute("SELECT * FROM panels") as cursor:
        panels = await cursor.fetchall()

    for p in panels:
        async with db.execute(
                "SELECT role_id, label, emoji, style FROM panel_roles WHERE panel_name = ?",
                (p[0],)
        ) as c:
            roles = await c.fetchall()

        panel_data = {"name": p[0], "type": p[4]}

        roles_data = [
            {"role_id": r[0], "label": r[1], "emoji": r[2], "style": r[3]}
            for r in roles
        ]

        message_id = p[6]

        if message_id:
            bot.add_view(
                RolePanelView(panel_data, roles_data),
                message_id=message_id
            )

async def rolepanel_create(ctx, name: str, typ: str):
    if typ not in ["buttons", "dropdown"]:
        return await ctx.send("❌ Typ muss `buttons` oder `dropdown` sein.")

    db = ctx.bot.roleconfig
    await db.execute(
        "INSERT OR IGNORE INTO panels (name, type) VALUES (?, ?)",
        (name, typ)
    )
    await db.commit()

    await ctx.send(f"✅ Panel `{name}` wurde erstellt.\n👉 Nutze `m!admin roleselection role_add`, um Rollen hinzuzufügen.")

async def rolepanel_addrole(ctx, panel: str, role: discord.Role):
    db = ctx.bot.roleconfig
    async with db.execute("SELECT name FROM panels WHERE name = ?", (panel,)) as c:
        exists = await c.fetchone()

    if not exists:
        return await ctx.send("❌ Panel existiert nicht.")

    async with db.execute(
            "SELECT * FROM panel_roles WHERE panel_name = ? AND role_id = ?",
            (panel, role.id)
    ) as c:
        already = await c.fetchone()

    if already:
        return await ctx.send("⚠️ Diese Rolle ist bereits im Panel.")

    await db.execute(
        "INSERT INTO panel_roles VALUES (?, ?, ?, ?, ?)",
        (panel, role.id, role.name, None, 1)
    )
    await db.commit()

    await ctx.send(f"✅ Rolle **{role.name}** wurde zum Panel `{panel}` hinzugefügt.")

async def rolepanel_removerole(ctx, panel: str, role: discord.Role):
    db = ctx.bot.roleconfig
    cursor = await db.execute(
        "DELETE FROM panel_roles WHERE panel_name = ? AND role_id = ?",
        (panel, role.id)
    )
    await db.commit()

    if cursor.rowcount == 0:
        return await ctx.send("⚠️ Diese Rolle ist nicht im Panel.")

    await ctx.send(f"🗑️ Rolle **{role.name}** wurde entfernt.")

async def rolepanel_send(ctx: commands.Context, panel: str):
    db = ctx.bot.roleconfig

    async with db.execute("SELECT * FROM panels WHERE name = ?", (panel,)) as c:
        p = await c.fetchone()

    if not p:
        return await ctx.send("❌ Panel nicht gefunden.")

    async with db.execute(
            "SELECT role_id, label, emoji, style FROM panel_roles WHERE panel_name = ?",
            (panel,)
    ) as c:
        roles = await c.fetchall()

    if not roles:
        return await ctx.send("⚠️ Dieses Panel hat keine Rollen.")

    config = await get_channel_config(ctx.bot.configdb, ctx.guild.id)

    panel_data = {"name": p[0], "type": p[4]}

    roles_data = [
        {"role_id": r[0], "label": r[1], "emoji": r[2], "style": r[3]}
        for r in roles
    ]
    if p[2]:
        desc = p[2].replace("|", "\n")
        description = desc
    else:
        description = "Wähle deine Rollen unten aus."

    embed = discord.Embed(
        title=p[1] or "🎭 Rollen auswählen",
        description=description,
        color=discord.Color.blue()
    )

    if p[3]:
        embed.set_footer(text=p[3])

    view = RolePanelView(panel_data, roles_data)

    msg_channel_id = config[6]
    msg_channel = ctx.bot.get_channel(msg_channel_id)

    msg = await msg_channel.send(embed=embed, view=view)

    await db.execute(
        "UPDATE panels SET channel_id = ?, message_id = ? WHERE name = ?",
        (msg_channel.id, msg.id, panel)
    )
    await db.commit()
    await ctx.reply("✅ Panel erfolgreich gesendet.")

async def rolepanel_edit(ctx: commands.Context, panel: str):
    db = ctx.bot.roleconfig

    async with db.execute("SELECT name FROM panels WHERE name = ?", (panel,)) as c:
        exists = await c.fetchone()

    if not exists:
        return await ctx.send("❌ Panel existiert nicht.")

    await ctx.reply(content="🔧 Klicke unten auf den Button, um das Modal zu öffnen und die Nachricht des Rolepanels einzustellen!", view=EditModalButton(panel, db))