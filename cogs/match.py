import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
import os
import asyncio
from typing import Optional

from utils.nba_api import get_scoreboard, get_boxscore, get_week_schedule
from utils.formatters import (
    build_game_announcement, build_final_score,
    build_boxscore, build_weekly_embeds
)

CHANNEL_MATCH = int(os.getenv("CHANNEL_NBA_MATCH", "0"))

# ── State tracking ────────────────────────────────────────────────────────────
_announced: set[str]           = set()   # game_ids announced (1h before)
_finalized: set[str]           = set()   # game_ids boxscored
_prev_state: dict[str, int]    = {}      # game_id → status_code last seen
_week_posted_on: str           = ""      # date string of last monday post


class MatchCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.score_loop.start()
        self.weekly_loop.start()

    def cog_unload(self):
        self.score_loop.cancel()
        self.weekly_loop.cancel()

    # ── Every 2 min: scoreboard check ────────────────────────────────────────

    @tasks.loop(minutes=2)
    async def score_loop(self):
        ch = self.bot.get_channel(CHANNEL_MATCH)
        if not ch:
            print("[Match] Channel not found.")
            return

        games = await get_scoreboard()
        if not games:
            print("[Match] No games today from scoreboard.")
            return

        for g in games:
            gid  = g["id"]
            code = g["status_code"]   # 1=scheduled 2=live 3=final
            txt  = g["status_text"]

            # ── 1h BEFORE: announce scheduled game ─────────────────────────
            # status_text for scheduled games looks like "7:30 pm ET"
            # We announce when status_code == 1 and we haven't announced yet
            if code == 1 and gid not in _announced:
                # Check if game is within ~65 minutes
                if self._is_within_one_hour(txt):
                    embed = build_game_announcement(g)
                    await ch.send(embed=embed)
                    _announced.add(gid)
                    await asyncio.sleep(1)

            # ── FINAL: post score + boxscore ───────────────────────────────
            elif code == 3 and gid not in _finalized:
                _finalized.add(gid)
                _announced.add(gid)   # mark as announced too

                # Final score embed
                score_embed = build_final_score(g)
                await ch.send(embed=score_embed)
                await asyncio.sleep(2)

                # Boxscore
                bs = await get_boxscore(gid)
                box_embeds = build_boxscore(g, bs)
                if box_embeds:
                    await ch.send(embeds=box_embeds[:4])

                # Trigger standings update
                await asyncio.sleep(5)
                self.bot.dispatch("game_finished", g)
                await asyncio.sleep(1)

            _prev_state[gid] = code

    @score_loop.before_loop
    async def _before_score(self):
        await self.bot.wait_until_ready()

    def _is_within_one_hour(self, status_text: str) -> bool:
        """Check if a scheduled game starts within the next 65 minutes."""
        import re
        from datetime import timezone
        # Parse time like "7:30 pm ET" or "19:30"
        m = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", status_text.lower())
        if not m:
            return False
        hour   = int(m.group(1))
        minute = int(m.group(2))
        ampm   = m.group(3)
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        # Convert ET to UTC (+5 normally, +4 during DST — approximate)
        hour_utc = (hour + 4) % 24

        now_utc = datetime.utcnow()
        target  = now_utc.replace(hour=hour_utc, minute=minute, second=0, microsecond=0)
        diff    = (target - now_utc).total_seconds() / 60

        return 0 <= diff <= 65

    # ── Every Monday 08:00: post weekly schedule ──────────────────────────────

    @tasks.loop(minutes=1)
    async def weekly_loop(self):
        global _week_posted_on
        now      = datetime.now()
        today    = now.strftime("%Y-%m-%d")
        if now.weekday() == 0 and now.hour == 8 and now.minute == 0 and _week_posted_on != today:
            _week_posted_on = today
            ch = self.bot.get_channel(CHANNEL_MATCH)
            if not ch:
                return
            schedule = await get_week_schedule()
            embeds   = build_weekly_embeds(schedule)
            for i in range(0, len(embeds), 10):
                await ch.send(embeds=embeds[i:i+10])
                await asyncio.sleep(1)

    @weekly_loop.before_loop
    async def _before_weekly(self):
        await self.bot.wait_until_ready()

    # ── Slash commands ────────────────────────────────────────────────────────

    @app_commands.command(name="nba_match", description="🏀 Scores et matchs du jour")
    async def nba_match(self, interaction: discord.Interaction):
        await interaction.response.defer()
        games = await get_scoreboard()
        if not games:
            return await interaction.followup.send(embed=discord.Embed(
                title="🏀 NBA — Matchs du jour",
                description="> Aucun match NBA aujourd'hui. 😴",
                color=0x17408B, timestamp=datetime.utcnow()
            ))
        embeds = [build_final_score(g) if g["status_code"] == 3 else build_game_announcement(g)
                  for g in games]
        await interaction.followup.send(embeds=embeds[:10])

    @app_commands.command(name="nba_week", description="🗓️ Programme NBA des 7 prochains jours")
    async def nba_week(self, interaction: discord.Interaction):
        await interaction.response.defer()
        schedule = await get_week_schedule()
        embeds   = build_weekly_embeds(schedule)
        await interaction.followup.send(embeds=embeds[:10])


async def setup(bot: commands.Bot):
    await bot.add_cog(MatchCog(bot))