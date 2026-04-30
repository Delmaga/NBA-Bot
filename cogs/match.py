import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, date
import os, asyncio

from utils.nba_api import get_scoreboard, get_boxscore, get_week_schedule
from utils.formatters import (
    build_weekly_embeds, build_game_announcement,
    build_live_score, build_boxscore
)

CHANNEL_MATCH = int(os.getenv("CHANNEL_NBA_MATCH", "0"))

# State tracking
_prev_scores: dict[str, tuple]  = {}   # game_id → (home_score, away_score, status_code)
_announced:   set[str]          = set() # game_ids already announced
_boxscored:   set[str]          = set() # game_ids already boxscored
_week_posted: str               = ""    # last Monday date we posted the schedule


class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.score_loop.start()
        self.weekly_loop.start()

    def cog_unload(self):
        self.score_loop.cancel()
        self.weekly_loop.cancel()

    # ── Every 2 minutes: check scores, announce games, post boxscores ─────────

    @tasks.loop(minutes=2)
    async def score_loop(self):
        ch = self.bot.get_channel(CHANNEL_MATCH)
        if not ch:
            return

        games = await get_scoreboard()
        if not games:
            print("[Match] Scoreboard returned 0 games.")
            return

        for g in games:
            gid    = g["id"]
            code   = g["status_code"]   # 1=scheduled 2=live 3=final
            h_s    = g["home_score"]
            a_s    = g["away_score"]

            # ── Announce game day (scheduled, not yet announced) ────────────
            if code == 1 and gid not in _announced:
                embed = build_game_announcement(g)
                await ch.send(embed=embed)
                _announced.add(gid)
                await asyncio.sleep(1)

            # ── Live: post score update only when score changes ─────────────
            elif code == 2:
                prev = _prev_scores.get(gid)
                curr = (h_s, a_s, code)
                if prev != curr:
                    _prev_scores[gid] = curr
                    embed = build_live_score(g)
                    await ch.send(embed=embed)
                    await asyncio.sleep(1)

            # ── Final: post boxscore once ───────────────────────────────────
            elif code == 3 and gid not in _boxscored:
                _boxscored.add(gid)
                bs = await get_boxscore(gid)
                embeds = build_boxscore(g, bs)
                await ch.send(content="**🏁  FIN DE MATCH !**", embeds=embeds[:4])

                # Trigger standings refresh
                await asyncio.sleep(5)
                self.bot.dispatch("standings_update", g)
                await asyncio.sleep(1)

    @score_loop.before_loop
    async def before_score(self):
        await self.bot.wait_until_ready()

    # ── Every Monday 08:00: post weekly schedule ──────────────────────────────

    @tasks.loop(minutes=1)
    async def weekly_loop(self):
        global _week_posted
        now = datetime.now()
        today_str = date.today().isoformat()
        if now.weekday() == 0 and now.hour == 8 and now.minute == 0 and _week_posted != today_str:
            _week_posted = today_str
            await self._post_week()

    @weekly_loop.before_loop
    async def before_weekly(self):
        await self.bot.wait_until_ready()

    async def _post_week(self):
        ch = self.bot.get_channel(CHANNEL_MATCH)
        if not ch:
            return
        schedule = await get_week_schedule()
        embeds = build_weekly_embeds(schedule)
        for i in range(0, len(embeds), 10):
            await ch.send(embeds=embeds[i:i+10])
            await asyncio.sleep(1)

    # ── Slash commands ────────────────────────────────────────────────────────

    @app_commands.command(name="nba_match", description="🏀 Scores et matchs du jour")
    async def nba_match(self, interaction: discord.Interaction):
        await interaction.response.defer()
        games = await get_scoreboard()

        if not games:
            embed = discord.Embed(
                title="🏀 NBA — Matchs du jour",
                description="> Aucun match NBA aujourd'hui. 😴",
                color=0x17408B, timestamp=datetime.utcnow()
            )
            return await interaction.followup.send(embed=embed)

        embeds = [build_live_score(g) for g in games]
        for i in range(0, min(len(embeds), 10), 10):
            await interaction.followup.send(embeds=embeds[i:i+10])

    @app_commands.command(name="nba_week", description="🗓️ Programme NBA des 7 prochains jours")
    async def nba_week(self, interaction: discord.Interaction):
        await interaction.response.defer()
        schedule = await get_week_schedule()
        embeds = build_weekly_embeds(schedule)
        await interaction.followup.send(embeds=embeds[:10])


async def setup(bot):
    await bot.add_cog(MatchCog(bot))