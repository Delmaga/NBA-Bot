import discord
from discord.ext import commands
import asyncio, os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN","")
if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN manquant dans le .env !")

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = ["cogs.match", "cogs.classement", "cogs.news"]


@bot.event
async def on_ready():
    print(f"\n{'='*52}")
    print(f"  🏀 NBA Bot Premium — ONLINE")
    print(f"  Connecté  : {bot.user}  ({bot.user.id})")
    print(f"  Serveurs  : {len(bot.guilds)}")
    print(f"{'='*52}\n")
    try:
        synced = await bot.tree.sync()
        names  = [s.name for s in synced]
        print(f"✅ {len(synced)} commande(s) synced : {names}\n")
    except Exception as e:
        print(f"❌ Sync: {e}")


async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"✅ Cog : {cog}")
            except Exception as e:
                print(f"❌ Cog {cog}: {e}")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())