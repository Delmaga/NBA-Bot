import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
import os

from utils.nba_api import get_standings
from utils.formatters import build_standings_embed

CHANNEL_CLASS = int(os.getenv("CHANNEL_NBA_CLASSEMENT", "0"))

_msg_west: int | None = None
_msg_east: int | None = None


class ClassementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.standings_loop.start()

    def cog_unload(self):
        self.standings_loop.cancel()

    # ── Auto-refresh every 20 min ─────────────────────────────────────────────

    @tasks.loop(minutes=20)
    async def standings_loop(self):
        await self._refresh()

    @standings_loop.before_loop
    async def before_standings(self):
        await self.bot.wait_until_ready()

    # ── Triggered by match cog after game ends ────────────────────────────────

    @commands.Cog.listener("on_standings_update")
    async def on_standings_update(self, finished_game: dict):
        await self._refresh()

    async def _refresh(self):
        global _msg_west, _msg_east
        ch = self.bot.get_channel(CHANNEL_CLASS)
        if not ch:
            return

        data = await get_standings()
        west_teams = data.get("West", [])
        east_teams = data.get("East", [])

        if not west_teams and not east_teams:
            print("[Classement] No standings data returned.")
            return

        west_embed = build_standings_embed(west_teams, "West")
        east_embed = build_standings_embed(east_teams, "East")

        for embed, msg_id_var, setter in [
            (west_embed, _msg_west, "west"),
            (east_embed, _msg_east, "east"),
        ]:
            msg_id = _msg_west if setter == "west" else _msg_east
            try:
                if msg_id:
                    msg = await ch.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                else:
                    raise Exception("no msg yet")
            except Exception:
                sent = await ch.send(embed=embed)
                if setter == "west":
                    _msg_west = sent.id
                else:
                    _msg_east = sent.id

    # ── Slash command ─────────────────────────────────────────────────────────

    @app_commands.command(name="nba_classement", description="🏆 Classements NBA West & East")
    async def nba_classement(self, interaction: discord.Interaction):
        await interaction.response.defer()

        data = await get_standings()
        west_teams = data.get("West", [])
        east_teams = data.get("East", [])

        if not west_teams and not east_teams:
            return await interaction.followup.send("❌ Impossible de récupérer les classements. Réessaie dans quelques instants.")

        header = discord.Embed(
            title="🏆  NBA STANDINGS — Saison 2024-25",
            description=(
                "> Classements officiels mis à jour en temps réel\n"
                "> `✦` Playoff direct  •  `◈` Play-In Tournament  •  `✖` Éliminé\n"
                f"{'━'*36}"
            ),
            color=0xE8174B,
            timestamp=datetime.utcnow(),
        )
        header.set_thumbnail(url="https://cdn.nba.com/logos/leagues/logo-nba.svg")

        embeds = [header]
        if west_teams:
            embeds.append(build_standings_embed(west_teams, "West"))
        if east_teams:
            embeds.append(build_standings_embed(east_teams, "East"))

        await interaction.followup.send(embeds=embeds)


async def setup(bot):
    await bot.add_cog(ClassementCog(bot))