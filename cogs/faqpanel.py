from discord.ext import commands
from discord import ui
import discord
import discord.utils
from setup_config_db import get_channel_config

faq_questions = {
    "🧭 Was ist MaxeySMP?": "q1",
    "📅 Wann startet der Server?": "q2",
    "👥 Wie viele Spieler können joinen?": "q3",
    "🧩 Welche Versionen werden unterstützt?": "q4",
    "🎙️ Simple Voice Chat": "q5",
    "🌐 Wie joine ich?": "q6",
    "⚔️ Ist PvP aktiviert?": "q8",
    "⭐ Welche Vorteile haben Subs?": "q10",
    "📸 Welche Vorteile haben Medias?": "q11",
    "🎁 Wie bekomme ich die Sub-Rolle?": "q12",
    "📹 Wie bekomme ich den Media-Rang?": "q13"
}

faq_answers = {
    "q1":"MaxeySMP ist ein Survival-Multiplayer-Server mit Auktionshaus, Orders und vielen weiteren SMP-üblichen Features. Unser Ziel ist es, den SMP so zu gestalten, dass er auch für Nicht-PvP-Spieler angenehm ist. Du kannst dort entspannt bauen, ohne Angst vor Griefing haben zu müssen.",
    "q2":"Der Release von MaxeySMP ist am Freitag, den 24. April 2026 (<t:1777024800:R>).",
    "q3":"Es gibt keine Whitelist. Wie viele Spieler gleichzeitig online sein können, hängt von den verfügbaren Serverressourcen ab. Wir sorgen aber dafür, dass möglichst viele gleichzeitig spielen können.",
    "q4":"Zum Start läuft MaxeySMP auf Version 1.21.11. Du kannst aber auch mit Versionen von 1.21.1 bis 1.21.11 joinen.",
    "q5": "Simple Voice Chat wird unterstützt, die Nutzung ist jedoch komplett freiwillig.",
    "q6":"**Java:** über maxeysmp.de\n**Bedrock:** über maxeysmp.de auf Port 19132",
    "q8": "Auf dem Haupt-SMP sind PvP und Griefing verboten. Für PvP-Fans wird es jedoch eigene Möglichkeiten geben, wie z.B. Duelle oder spezielle PvP-Spielmodi.",
    "q10":"Als Sub bekommst du zusätzliche Befehle auf dem Server (z.B. /trash oder /rename) und kannst jederzeit joinen – selbst wenn der Server voll ist. Außerdem wirst du auf dem Server besonders hervorgehoben.",
    "q11":"Als Media erhältst du kostenlos alle Features der Sub-Rolle und wirst in der Tabliste zusätzlich weiter oben angezeigt.",
    "q12":"Verbinde deinen Discord-Account mit deinem Twitch-Account, über den du subbst. \nDanach musst du nur noch hier deinen Minecraft-Account verknüpfen: https://discord.com/channels/1476359827176423426/1489947203744043198.\nAnschließend erhältst du automatisch deine Sub-Rolle ingame.",
    "q13":"Eröffne ein Ticket im Discord und sende dort deinen Kanal ein: https://discord.com/channels/1476359827176423426/1479885668908797982. \n"
          "Um den Media-Rang zu erhalten, muss mindestens eine der folgenden Anforderungen erfüllt sein:\n\n- Mindestens 20 durchschnittliche Zuschauer im Stream\n- Mindestens 80 durchschnittliche Zuschauer bei TikTok-Streams\n- Mindestens 3.000 Aufrufe auf einem YouTube-Video\n- Mindestens 50.000 Aufrufe auf TikTok, YouTube Shorts oder Instagram Reels\n\n Hast du diese Aufrufe erreicht? Öffne ein Ticket, um deinen Rang zu erhalten!"
}

class FAQSelect(ui.Select):
    def __init__(self):
        super().__init__(custom_id="faq_select", placeholder="Wähle eine Frage aus...", max_values=1)
        self.options = []
        for question, value in faq_questions.items():
            self.options.append(discord.SelectOption(label=question, value=value))

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value not in faq_answers:
            return await interaction.response.send_message("❌ Du hast eine Frage ausgewählt, die nicht existiert...", ephemeral=True)
        label = next(opt.label for opt in self.options if opt.value == value)
        answer = faq_answers[value]

        if interaction.message.flags.ephemeral:
            await interaction.response.edit_message(view=AnswerMessageLayout(label, answer))

        else:
            await interaction.response.send_message(view=AnswerMessageLayout(label, answer), ephemeral=True)

            try:
                await interaction.message.edit(view=self.view)
            except Exception:
                pass

class AnswerMessageLayout(ui.LayoutView):
    def __init__(self, label, answer):
        super().__init__()
        self.label = label
        self.answer = answer

        container = ui.Container()
        container.add_item(ui.TextDisplay(f"## {label}"))
        seperator = ui.Separator()
        answer_text = ui.TextDisplay(answer)
        container.add_item(answer_text)

        row = ui.ActionRow()
        row.add_item(FAQSelect())

        self.add_item(container)
        self.add_item(seperator)
        self.add_item(row)


class FAQLayout(ui.LayoutView):
    def __init__(self, guild_icon_url: str):
        super().__init__(timeout=None)

        top_container = ui.Container()
        top_container.add_item(ui.MediaGallery().add_item(media="https://i.ibb.co/chzScfhp/faq.png"))

        seperator1= ui.Separator()

        s1 = ui.TextDisplay(
            "### ❓ Wähle eine Frage unten aus.\n"
            "Wenn deine Frage hier nicht beantwortet wurde, kannst du jederzeit ein Ticket im Discord öffnen – dir wird auf jeden Fall jemand helfen."
        )
        top_container.add_item(s1)

        row = ui.ActionRow()
        row.add_item(FAQSelect())

        self.add_item(top_container)
        self.add_item(seperator1)
        self.add_item(row)

async def send_faq_panel(bot: commands.Bot, guild: discord.Guild, channel: discord.TextChannel = None):
    if channel is None:
        config = await get_channel_config(bot.configdb, guild.id)
        channel_id = config[1]
        channel = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)

    try:
        await channel.send(view=FAQLayout(guild.icon.url))
    except discord.Forbidden:
        pass

class FAQCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        view = ui.View(timeout=None)
        view.add_item(FAQSelect())
        self.bot.add_view(view)
        self.bot.add_view(FAQLayout(guild_icon_url="https://cdn.discordapp.com/icons/1476359827176423426/3716f55d62881f2a165a8fcbc5dd972d.webp?size=96&quality=lossless"))


async def setup(bot):
    await bot.add_cog(FAQCog(bot))


