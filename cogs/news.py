import discord
from discord.ext import commands, tasks
from discord import app_commands
import os, asyncio, random

from utils.news_feed import fetch_all_articles, detect_category
from utils.ai_summary import summarize
from utils.formatters import build_news_embed

CHANNEL_NEWS = int(os.getenv("CHANNEL_NBA_NEWS", "0"))
IMAGE_RATE   = 0.5   # 50% of posts include an image


class NewsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.news_loop.start()

    def cog_unload(self):
        self.news_loop.cancel()

    @tasks.loop(minutes=15)
    async def news_loop(self):
        ch = self.bot.get_channel(CHANNEL_NEWS)
        if not ch:
            return

        articles = await fetch_all_articles(max_per_feed=4)

        for art in articles[:10]:
            title   = art.get("title","").strip()
            content = art.get("content","").strip()
            if not title or len(title) < 5:
                continue

            category = detect_category(title, content)
            summary  = await summarize(title, content, category)
            img      = art.get("image_url") if random.random() < IMAGE_RATE else None

            embed = build_news_embed(
                title, summary,
                art.get("source","?"),
                img, category,
                art.get("published","")
            )
            try:
                await ch.send(embed=embed)
                await asyncio.sleep(4)
            except discord.HTTPException as e:
                print(f"[News] send error: {e}")

    @news_loop.before_loop
    async def before_news(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="nba_news", description="📰 Dernières actualités NBA")
    async def nba_news(self, interaction: discord.Interaction):
        await interaction.response.defer()
        articles = await fetch_all_articles(max_per_feed=2)

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


async def setup(bot):
    await bot.add_cog(NewsCog(bot))