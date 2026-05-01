import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import random
from typing import Optional

from utils.news_feed import fetch_all_articles, detect_category
from utils.ai_summary import summarize
from utils.formatters import build_news_embed

CHANNEL_NEWS = int(os.getenv("CHANNEL_NBA_NEWS", "0"))
IMAGE_RATE   = 0.5   # 50% des posts ont une image


class NewsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.news_loop.start()

    def cog_unload(self):
        self.news_loop.cancel()

    # ── Every 10 min: fetch & post new articles ───────────────────────────────

    @tasks.loop(minutes=10)
    async def news_loop(self):
        ch = self.bot.get_channel(CHANNEL_NEWS)
        if not ch:
            print("[News] Channel not found.")
            return

        articles = await fetch_all_articles(max_per_feed=4)
        if not articles:
            return

        for art in articles[:8]:
            title   = (art.get("title","") or "").strip()
            content = (art.get("content","") or "").strip()

            if not title or len(title) < 5:
                continue

            # Proper category detection (not always injury!)
            category = detect_category(title, content)

            # AI summary
            summary = await summarize(title, content, category)

            # 50% image
            img = art.get("image_url") if random.random() < IMAGE_RATE else None

            embed = build_news_embed(
                title, summary,
                art.get("source", "?"),
                img, category,
                art.get("published", "")
            )
            try:
                await ch.send(embed=embed)
                await asyncio.sleep(4)
            except discord.HTTPException as e:
                print(f"[News] send error: {e}")

    @news_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    # ── Slash command ─────────────────────────────────────────────────────────

    @app_commands.command(name="nba_news", description="📰 Dernières actualités NBA")
    async def nba_news(self, interaction: discord.Interaction):
        await interaction.response.defer()
        articles = await fetch_all_articles(max_per_feed=2)
        if not articles:
            return await interaction.followup.send("❌ Aucune actu disponible.")

        embeds = []
        for art in articles[:5]:
            title    = (art.get("title","") or "").strip()
            content  = (art.get("content","") or "").strip()
            if not title:
                continue
            category = detect_category(title, content)
            summary  = await summarize(title, content, category)
            img      = art.get("image_url") if random.random() < IMAGE_RATE else None
            embeds.append(build_news_embed(
                title, summary, art.get("source","?"),
                img, category, art.get("published","")
            ))

        if embeds:
            await interaction.followup.send(embeds=embeds[:10])
        else:
            await interaction.followup.send("❌ Aucune actu disponible.")


async def setup(bot: commands.Bot):
    await bot.add_cog(NewsCog(bot))