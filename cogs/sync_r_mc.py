import aiohttp
from discord.ext import commands
import discord
from setup_link_db import get_linking
from setup_config_db import get_role_config, get_syncroles_webserver_config

class sync_r_mc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def update_minecraft_role(self, uuid, role_key, action):
        syncroles_config = await get_syncroles_webserver_config(self.bot.configdb)
        if not syncroles_config:
            print("[SyncRoles] Konfiguration konnte nicht geladen werden.")
            return

        url, password = syncroles_config[0], syncroles_config[1]

        params = {
            "uuid": uuid,
            "action": action,
            "role": role_key,
            "key": password
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        print(f"[SyncRoles] Erfolg! {role_key} {action} für {uuid}: {text}")
                    elif resp.status == 403:
                        print(f"[SyncRoles] Fehler: Passwort (Key) wurde vom Server abgelehnt.")
                    else:
                        print(f"[SyncRoles] Server antwortete mit Status: {resp.status}")
        except Exception as e:
            print(f"[SyncRoles] Verbindung zum MC-Server fehlgeschlagen: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        config = await get_role_config(self.bot.configdb, after.guild.id)
        if not config:
            return

        roles_to_check = {
            "sub": config[9],
            "builder": config[12],
            "mod": config[1]
        }

        for role_key, role_id in roles_to_check.items():
            if not role_id: continue

            had_role = any(r.id == int(role_id) for r in before.roles)
            has_role = any(r.id == int(role_id) for r in after.roles)

            if had_role != has_role:
                uuid = await get_linking(self.bot.linking_db, discord_id=after.id)
                if uuid:
                    action = "add" if has_role else "remove"
                    await self.update_minecraft_role(uuid, role_key, action)

async def setup(bot):
    await bot.add_cog(sync_r_mc(bot))