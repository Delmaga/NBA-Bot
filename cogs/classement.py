import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
import os
import asyncio

from utils.nba_api import get_standings_regular, get_standings_playoff, get_standings_playin
from utils.formatters import build_standings_embed

CHANNEL_CLASS = int(os.getenv("CHANNEL_NBA_CLASSEMENT", "0"))

# Store message IDs so we EDIT instead of reposting every time
_msg_ids: dict[str, int | None] = {
    "reg_west": None, "reg_east": None,
    "po_west":  None, "po_east":  None,
    "pi_west":  None, "pi_east":  None,
}


class ClassementCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.standings_loop.start()

    def cog_unload(self):
        self.standings_loop.cancel()

    # ── Auto-refresh every 15 min ─────────────────────────────────────────────

    @tasks.loop(minutes=15)
    async def standings_loop(self):
        await self._refresh_all()

    @standings_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    # ── Triggered after a game finishes ──────────────────────────────────────

    @commands.Cog.listener("on_game_finished")
    async def on_game_finished(self, game: dict):
        print(f"[Classement] Refreshing after game: {game['away_abbr']} @ {game['home_abbr']}")
        await self._refresh_all()

    async def _refresh_all(self):
        ch = self.bot.get_channel(CHANNEL_CLASS)
        if not ch:
            print("[Classement] Channel not found.")
            return

        # Fetch all three types in parallel
        reg, po, pi = await asyncio.gather(
            get_standings_regular(),
            get_standings_playoff(),
            get_standings_playin(),
        )

        tasks_list = [
            ("reg_west", reg.get("West",[]), "West", "Regular Season"),
            ("reg_east", reg.get("East",[]), "East", "Regular Season"),
            ("po_west",  po.get("West",[]),  "West", "Playoffs"),
            ("po_east",  po.get("East",[]),  "East", "Playoffs"),
            ("pi_west",  pi.get("West",[]),  "West", "PlayIn"),
            ("pi_east",  pi.get("East",[]),  "East", "PlayIn"),
        ]

        for key, teams, conf, stype in tasks_list:
            if not teams:
                continue
            embed = build_standings_embed(teams, conf, stype)
            msg_id = _msg_ids.get(key)
            try:
                if msg_id:
                    msg = await ch.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                else:
                    raise Exception("no msg")
            except Exception:
                sent = await ch.send(embed=embed)
                _msg_ids[key] = sent.id
            await asyncio.sleep(0.5)

    # ── Slash command ─────────────────────────────────────────────────────────

    @app_commands.command(name="nba_classement", description="🏆 Classements NBA (Saison, Playoffs, Play-In)")
    async def nba_classement(self, interaction: discord.Interaction):
        await interaction.response.defer()

        reg, po, pi = await asyncio.gather(
            get_standings_regular(),
            get_standings_playoff(),
            get_standings_playin(),
        )

        embeds = []

        header = discord.Embed(
            title="🏆  NBA STANDINGS — Saison 2024-25",
            description=(
                "> Classements officiels mis à jour automatiquement\n"
                "> `✦` Playoff direct  •  `◈` Play-In  •  `✖` Éliminé\n"
                f"{'━'*36}"
            ),
            color=0xE8174B, timestamp=datetime.utcnow(),
        )
        header.set_thumbnail(url="https://cdn.nba.com/logos/leagues/logo-nba.svg")
        embeds.append(header)

        for teams, conf, stype in [
            (reg.get("West",[]), "West", "Regular Season"),
            (reg.get("East",[]), "East", "Regular Season"),
            (po.get("West",[]),  "West", "Playoffs"),
            (po.get("East",[]),  "East", "Playoffs"),
            (pi.get("West",[]),  "West", "PlayIn"),
            (pi.get("East",[]),  "East", "PlayIn"),
        ]:
            if teams:
                embeds.append(build_standings_embed(teams, conf, stype))

        # Discord max 10 embeds per message
        for i in range(0, len(embeds), 10):
            if i == 0:
                await interaction.followup.send(embeds=embeds[i:i+10])
            else:
                await interaction.channel.send(embeds=embeds[i:i+10])


async def setup(bot: commands.Bot):
    await bot.add_cog(ClassementCog(bot))