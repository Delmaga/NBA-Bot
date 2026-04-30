import discord
from discord.ext import commands, tasks
from datetime import datetime
import os
import asyncio
import random

from utils.news_feed import fetch_rss, fetch_newsapi, detect_category, CAT_EMOJI
from utils.ai_summary import summarize
from utils.formatters import build_news_embed

CHANNEL_NEWS = int(os.getenv("CHANNEL_NBA_NEWS", "0"))

# Probability of including an image (50% as requested)
IMAGE_RATE = 0.5


class News(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.news_loop.start()

    def cog_unload(self):
        self.news_loop.cancel()

    # ── Every 15 min → fetch & post new articles ──────────────────────────────

    @tasks.loop(minutes=15)
    async def news_loop(self):
        ch = self.bot.get_channel(CHANNEL_NEWS)
        if not ch:
            return

        # Gather from RSS + NewsAPI
        articles = await fetch_rss(max_per_feed=3)
        articles += await fetch_newsapi("NBA basketball", "en")
        articles += await fetch_newsapi("NBA basketball", "fr")

        # Shuffle to mix sources
        random.shuffle(articles)

        for art in articles[:12]:
            title   = art.get("title","")
            content = art.get("content","")
            source  = art.get("source","?")
            pub     = art.get("published","")

            if not title:
                continue

            # Detect category
            category = detect_category(title, content)

            # AI summary
            summary = await summarize(title, content, category)

            # 50% chance to use image
            img = art.get("image_url") if random.random() < IMAGE_RATE else None

            embed = build_news_embed(title, summary, source, img, category, pub)

            try:
                await ch.send(embed=embed)
                await asyncio.sleep(3)  # avoid rate limits
            except discord.HTTPException as e:
                print(f"[News] Failed to send: {e}")

    @news_loop.before_loop
    async def before_news(self):
        await self.bot.wait_until_ready()

    # ── Slash command: /nba_news ──────────────────────────────────────────────

    @discord.app_commands.command(name="nba_news", description="📰 Dernières actualités NBA")
    async def nba_news(self, interaction: discord.Interaction):
        await interaction.response.defer()

        articles = await fetch_rss(max_per_feed=2)
        articles += await fetch_newsapi("NBA", "fr")

        if not articles:
            return await interaction.followup.send("❌ Aucune actu disponible pour le moment.")

        embeds = []
        for art in articles[:5]:
            title    = art.get("title","")
            content  = art.get("content","")
            category = detect_category(title, content)
            summary  = await summarize(title, content, category)
            img      = art.get("image_url") if random.random() < IMAGE_RATE else None
            embeds.append(build_news_embed(title, summary, art.get("source","?"), img, category, art.get("published","")))

        await interaction.followup.send(embeds=embeds[:10])


async def setup(bot: commands.Bot):
    await bot.add_cog(News(bot))
