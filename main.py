import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "")
if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN manquant dans le .env !")

# ── Intents ───────────────────────────────────────────────────────────────────
# NOTE: Va sur discord.com/developers/applications → ton bot → Bot
#       et active les 3 "Privileged Gateway Intents" (Presence, Server Members, Message Content)
intents = discord.Intents.default()
# On n'utilise PAS members ni message_content (pas nécessaire pour slash commands)
# Si tu les actives dans le portail tu peux les décommenter ici :
# intents.members = True
# intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = ["cogs.match", "cogs.classement", "cogs.news"]


@bot.event
async def on_ready():
    print(f"\n{'='*50}")
    print(f"  🏀 NBA Bot Premium — ONLINE")
    print(f"  Connecté : {bot.user} ({bot.user.id})")
    print(f"  Serveurs : {len(bot.guilds)}")
    print(f"{'='*50}\n")

    # Sync ici = Discord est prêt, application_id connu
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash command(s) synchronisée(s) : {[s.name for s in synced]}")
    except Exception as e:
        print(f"❌ Sync commands : {e}")


async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"✅ Cog chargé : {cog}")
            except Exception as e:
                print(f"❌ Cog {cog} : {e}")

        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())