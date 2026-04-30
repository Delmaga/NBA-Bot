import discord
from discord.ext import commands, tasks
from datetime import datetime, date, timedelta
import os
import asyncio

from utils.nba_api import (
    get_today_games, get_live_games, get_game_stats, get_week_games, get_games_for_date,
    emoji, color, logo
)
from utils.formatters import (
    build_weekly_schedule, build_game_announcement,
    build_live_score, build_boxscore, build_standings
)
from utils.nba_api import get_standings

CHANNEL_MATCH = int(os.getenv("CHANNEL_NBA_MATCH", "0"))

# Track live game states: game_id → last score tuple
_live_states: dict[int, tuple] = {}
_finished_ids: set[int]        = set()
_announced_today: set[int]     = set()


class Match(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.weekly_post.start()
        self.live_tracker.start()
        self.game_announcer.start()

    def cog_unload(self):
        self.weekly_post.cancel()
        self.live_tracker.cancel()
        self.game_announcer.cancel()

    # ── Every Monday 08:00 → post week schedule ──────────────────────────────

    @tasks.loop(minutes=1)
    async def weekly_post(self):
        now = datetime.now()
        if now.weekday() == 0 and now.hour == 8 and now.minute == 0:
            await self._post_weekly_schedule()

    @weekly_post.before_loop
    async def before_weekly(self):
        await self.bot.wait_until_ready()

    async def _post_weekly_schedule(self):
        ch = self.bot.get_channel(CHANNEL_MATCH)
        if not ch:
            return
        games = await get_week_games()
        # Group by date
        by_day: dict[str, list] = {}
        today = date.today()
        for i in range(7):
            by_day[(today + timedelta(days=i)).isoformat()] = []
        for g in games:
            d = g.get("_date") or date.today().isoformat()
            if d in by_day:
                by_day[d].append(g)

        embeds = build_weekly_schedule(by_day)
        await ch.send(embeds=embeds[:10])

    # ── Every day, announce games a few minutes before they start ────────────

    @tasks.loop(minutes=5)
    async def game_announcer(self):
        ch = self.bot.get_channel(CHANNEL_MATCH)
        if not ch:
            return
        games = await get_today_games()
        for g in games:
            gid = g.get("id")
            if gid in _announced_today:
                continue
            # Only announce scheduled games (not yet live or final)
            status = g.get("status","")
            if status and status != "Final" and ":" in str(status):
                embed = build_game_announcement(g)
                await ch.send(embed=embed)
                _announced_today.add(gid)
                await asyncio.sleep(1)

    @game_announcer.before_loop
    async def before_announcer(self):
        await self.bot.wait_until_ready()

    # ── Every 3 minutes → track live scores + post boxscore on finish ────────

    @tasks.loop(minutes=3)
    async def live_tracker(self):
        ch = self.bot.get_channel(CHANNEL_MATCH)
        if not ch:
            return

        live_games = await get_live_games()

        for g in live_games:
            gid    = g.get("id")
            h_s    = g.get("home_team_score", 0) or 0
            a_s    = g.get("visitor_team_score", 0) or 0
            status = g.get("status","")

            # Game just ended → post boxscore
            if status == "Final" and gid not in _finished_ids:
                _finished_ids.add(gid)
                stats  = await get_game_stats(gid)
                embeds = build_boxscore(g, stats)
                await ch.send(content="**🏁 FIN DE MATCH !**", embeds=embeds[:4])

                # Update standings for the affected conference
                await asyncio.sleep(10)
                await self._refresh_standings(g)
                continue

            # Live score update (only if score changed)
            prev = _live_states.get(gid)
            curr = (h_s, a_s)
            if prev != curr:
                _live_states[gid] = curr
                embed = build_live_score(g)
                await ch.send(embed=embed)

    @live_tracker.before_loop
    async def before_tracker(self):
        await self.bot.wait_until_ready()

    async def _refresh_standings(self, finished_game: dict):
        """Post updated standings for the conference of the finished game."""
        ch = self.bot.get_channel(int(os.getenv("CHANNEL_NBA_CLASSEMENT","0")))
        if not ch:
            return
        h_abbr = (finished_game.get("home_team") or {}).get("abbreviation","")
        from utils.nba_api import WEST
        conf = "West" if h_abbr in WEST else "East"

        standings = await get_standings()
        embed = build_standings(standings, conf)
        embed.title = f"🔄  CLASSEMENT MIS À JOUR — {'🌅 Western' if conf=='West' else '🌆 Eastern'} Conference"
        await ch.send(embed=embed)

    # ── Slash command: /nba_match ─────────────────────────────────────────────

    @discord.app_commands.command(name="nba_match", description="📅 Matchs du jour + programme de la semaine")
    async def nba_match(self, interaction: discord.Interaction):
        await interaction.response.defer()
        games = await get_today_games()

        if not games:
            embed = discord.Embed(
                title="🏀 NBA — Matchs du jour",
                description="> Aucun match aujourd'hui. 😴",
                color=0x17408B, timestamp=datetime.utcnow()
            )
            return await interaction.followup.send(embed=embed)

        embeds = [build_live_score(g) for g in games[:10]]
        await interaction.followup.send(embeds=embeds)

    # ── Slash command: /nba_week ──────────────────────────────────────────────

    @discord.app_commands.command(name="nba_week", description="🗓️ Programme des 7 prochains jours")
    async def nba_week(self, interaction: discord.Interaction):
        await interaction.response.defer()
        games = await get_week_games()
        by_day: dict[str, list] = {}
        today = date.today()
        for i in range(7):
            by_day[(today + timedelta(days=i)).isoformat()] = []
        for g in games:
            d = g.get("_date") or date.today().isoformat()
            if d in by_day:
                by_day[d].append(g)
        embeds = build_weekly_schedule(by_day)
        await interaction.followup.send(embeds=embeds[:10])


async def setup(bot: commands.Bot):
    await bot.add_cog(Match(bot))
