from discord import ui
from discord.ext import commands
from setup_config_db import get_channel_config
import discord


class AnswerLayoutView(ui.LayoutView):
    def __init__(self, rules: str, rule_title: str, icon_url: str):
        super().__init__()
        self.rules = rules

        answercontainer = ui.Container(accent_color=None)

        title = ui.TextDisplay(f"## {rule_title}")
        answercontainer.add_item(title)

        answercontainer.add_item(ui.Separator())

        answer = ui.TextDisplay(rules)
        answercontainer.add_item(answer)

        self.add_item(answercontainer)

class RuleLayout(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)

        top_container = ui.Container()

        image = ui.MediaGallery()
        image.add_item(media="https://i.ibb.co/wrKb7Jtv/REGELN.png")
        top_container.add_item(image)

        top_container.add_item(ui.Separator())

        s1=ui.TextDisplay("❗ Das Regelwerk gilt für alle Spieler – im Ingame-Chat, VoiceChat und auf dem gesamten MaxeySMP Server.")
        top_container.add_item(s1)
        top_container.add_item(ui.Separator())

        s2 = ui.TextDisplay("***WICHTIG:*** Das Team kann jederzeit Maßnahmen ergreifen – auch bei nicht explizit genannten Fällen.\n"
                            "**📣 Mit dem Betreten von MaxeySMP akzeptierst du alle folgenden Regeln.**")
        top_container.add_item(s2)
        top_container.add_item(ui.Separator())



        rules_buttons = [
            ("Verhalten & Chat", "🗨️", "rule_1"),
            ("Gameplay Regeln", "🎮", "rule_2"),
            ("PvP Regeln", "⚔️", "rule_3"),
            ("Cheats & Mods", "🧩", "rule_4"),
            ("Accounts & Handel", "🤝", "rule_5")
        ]

        rules_buttons_row1=ui.ActionRow()
        rules_buttons_row2=ui.ActionRow()

        for i, (label, emoji, c_id) in enumerate(rules_buttons):
            btn = ui.Button(label=label, emoji=emoji, custom_id=c_id, style=discord.ButtonStyle.secondary)

            btn.callback = self.rule_button_callback

            if i < 2:
                rules_buttons_row1.add_item(btn)
            else:
                rules_buttons_row2.add_item(btn)

        top_container.add_item(rules_buttons_row1)
        top_container.add_item(rules_buttons_row2)

        self.add_item(top_container)

    async def rule_button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data['custom_id']

        responses = {
            "rule_1": "§1.1 Respekt gegenüber allen Spielern und dem Team.\n"
                      "§1.2 Keine Diskriminierung (Rassismus, Sexismus, etc.).\n"
                      "§1.3 Keine unangemessenen Inhalte (Skins, Namen, Builds).\n"
                      "§1.4 Kein Nachahmen von Teammitgliedern.\n"
                      "§1.5 Kein Spam, Flooding oder CAPS-Missbrauch.\n"
                      "§1.6 Werbung nur mit Erlaubnis.\n"
                      "§1.7 Keine privaten Daten ohne Zustimmung teilen.\n"
                      "§1.8 Keine NSFW- oder Gore-Inhalte.\n§1.9 Support nicht missbrauchen.\n§1.10 Gesunder Menschenverstand gilt immer.",
            "rule_2": "§2.1 Keine AFK-Farmen mit Makros/Skripten.\n"
                      "§2.2 Keine Bugs, Glitches oder Dupes ausnutzen.\n"
                      "§2.3 Bugs müssen gemeldet werden.\n"
                      "§2.4 Kein absichtliches Laggen oder Crashen.\n"
                      "§2.5 Kein Seed-Cracking oder Seed-Abuse.\n§2.6 Keine unfairen Automationen.\n§2.7 Keine Umgehung von Systemen.",
            "rule_3": "§3.1 SMP: Kein PvP, kein Töten.\n"
                      "§3.2 Kein Griefing oder Raiding.\n"
                      "§3.3 Auch Versuche werden bestraft.\n§3.4 Keine Fallen oder zerstörerische Mechaniken.\n"
                      "§3.5 Keine Regel-Umgehung durch Bugs.\n§3.6 FFA: PvP erlaubt, kein Teaming.\n§3.7 Kein Spawn-Killing.\n"
                      "§3.8 Kein Combat-Logging.\n§3.9 Keine Bug- oder Map-Abuse.\n§3.10 Kein Boosting oder Stat-Manipulation.\n§3.11 Duels: Nur faire 1vs1.\n§3.12 Leave = Niederlage.\n"
                      "§3.13 Kein Weglaufen ohne Kampf.\n§3.14 Keine Bugs oder Exploits.",
            "rule_4": "§4.1 Cheats/Hacks sind verboten.\n§4.2 Beispiele:\n- X-Ray, ESP, Freecam\n- KillAura, Reach\n- Fly, Speed, Bhop\n- AutoClicker, Makros\n- AutoFarm, AutoFish\n- Inventory-Automation\n- Radar/Map Mods\n"
                      "§4.3 Cheaten vortäuschen = Bann.\n§4.4 Keine unfaire Spielvorteile",
            "rule_5": "§5.1 Kein Echtgeldhandel.\n§5.2 Kein Cross-Trading.\n§5.3 Kein Ban-Umgehen (VPN, Alts).\n§5.4 Kein Multi-Account-Missbrauch.",
        }

        titles = {
            "rule_1": "🗨️ Verhaltensregeln und Chat",
            "rule_2": "🎮 Ingame-Regeln",
            "rule_3": "⚔️ Verhalten beim PvP",
            "rule_4": "🧩 Modregeln und Cheats",
            "rule_5": "🤝 Handelsregeln und Accounts"

        }

        content = responses.get(custom_id)
        await interaction.response.send_message(view=AnswerLayoutView(content, titles.get(custom_id), interaction.guild.icon.url), ephemeral=True)


class RuleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(RuleLayout())

async def setup(bot):
    await bot.add_cog(RuleCog(bot))

async def send_rule_panel(bot: commands.Bot, guild: discord.Guild, channel: discord.TextChannel = None):
    if channel is None:
        config = await get_channel_config(bot.configdb, guild.id)
        channel_id = config[10]
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)

    try:
        await channel.send(view=RuleLayout())
    except discord.Forbidden:
        pass

