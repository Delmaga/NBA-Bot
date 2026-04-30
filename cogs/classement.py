import discord
from discord.ext import commands, tasks
from datetime import datetime
import os

from utils.nba_api import get_standings
from utils.formatters import build_standings

CHANNEL_CLASS = int(os.getenv("CHANNEL_NBA_CLASSEMENT", "0"))

# Store message IDs so we can EDIT them instead of reposting
_msg_west_id: int | None = None
_msg_east_id: int | None = None


class Classement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auto_update.start()

    def cog_unload(self):
        self.auto_update.cancel()

    # ── Every 30 min → edit the standings messages ────────────────────────────

    @tasks.loop(minutes=30)
    async def auto_update(self):
        await self._post_or_edit_standings()

    @auto_update.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

    async def _post_or_edit_standings(self):
        global _msg_west_id, _msg_east_id
        ch = self.bot.get_channel(CHANNEL_CLASS)
        if not ch:
            return

        standings = await get_standings()
        if not standings:
            return

        west_embed = build_standings(standings, "West")
        east_embed = build_standings(standings, "East")

        # Try to edit existing messages, otherwise post new
        for conf, embed, msg_id_attr in [
            ("West", west_embed, "_msg_west_id"),
            ("East", east_embed, "_msg_east_id"),
        ]:
            msg_id = globals()[msg_id_attr]
            try:
                if msg_id:
                    msg = await ch.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                else:
                    raise ValueError("No message yet")
            except Exception:
                sent = await ch.send(embed=embed)
                globals()[msg_id_attr] = sent.id

    # ── Slash command: /nba_classement ───────────────────────────────────────

    @discord.app_commands.command(name="nba_classement", description="🏆 Classements NBA West & East")
    async def nba_classement(self, interaction: discord.Interaction):
        await interaction.response.defer()
        standings = await get_standings()
        if not standings:
            return await interaction.followup.send("❌ Impossible de récupérer les classements.")

        west = build_standings(standings, "West")
        east = build_standings(standings, "East")

        header = discord.Embed(
            title="🏆  NBA STANDINGS — Saison 2024-25",
            description=(
                "> Classements officiels mis à jour en temps réel\n"
                "> `✦` Playoff direct  •  `◈` Play-In Tournament\n"
                f"{'━'*36}"
            ),
            color=0xE8174B,
            timestamp=datetime.utcnow(),
        )
        header.set_thumbnail(url="https://cdn.nba.com/logos/leagues/logo-nba.svg")
        await interaction.followup.send(embeds=[header, west, east])


async def setup(bot: commands.Bot):
    await bot.add_cog(Classement(bot))
