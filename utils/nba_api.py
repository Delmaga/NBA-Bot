import aiohttp
import os
from datetime import date, timedelta
from typing import Optional

BASE = "https://api.balldontlie.io/v1"
KEY  = os.getenv("BALLDONTLIE_KEY", "")

# ── Static data ───────────────────────────────────────────────────────────────

TEAM_EMOJIS = {
    "Atlanta Hawks":"🦅","Boston Celtics":"☘️","Brooklyn Nets":"🕸️",
    "Charlotte Hornets":"🐝","Chicago Bulls":"🐂","Cleveland Cavaliers":"⚔️",
    "Dallas Mavericks":"🤠","Denver Nuggets":"⛏️","Detroit Pistons":"🔩",
    "Golden State Warriors":"🌉","Houston Rockets":"🚀","Indiana Pacers":"🏎️",
    "LA Clippers":"⛵","Los Angeles Lakers":"👑","Memphis Grizzlies":"🐻",
    "Miami Heat":"🔥","Milwaukee Bucks":"🦌","Minnesota Timberwolves":"🐺",
    "New Orleans Pelicans":"🦩","New York Knicks":"🗽","Oklahoma City Thunder":"⚡",
    "Orlando Magic":"✨","Philadelphia 76ers":"🔔","Phoenix Suns":"☀️",
    "Portland Trail Blazers":"🌲","Sacramento Kings":"♛","San Antonio Spurs":"🏴",
    "Toronto Raptors":"🦖","Utah Jazz":"🎵","Washington Wizards":"🧙",
}

TEAM_COLORS = {
    "Atlanta Hawks":0xE03A3E,"Boston Celtics":0x007A33,"Brooklyn Nets":0x111111,
    "Charlotte Hornets":0x1D1160,"Chicago Bulls":0xCE1141,"Cleveland Cavaliers":0x860038,
    "Dallas Mavericks":0x00538C,"Denver Nuggets":0x0E2240,"Detroit Pistons":0xC8102E,
    "Golden State Warriors":0x1D428A,"Houston Rockets":0xCE1141,"Indiana Pacers":0x002D62,
    "LA Clippers":0xC8102E,"Los Angeles Lakers":0x552583,"Memphis Grizzlies":0x5D76A9,
    "Miami Heat":0x98002E,"Milwaukee Bucks":0x00471B,"Minnesota Timberwolves":0x0C2340,
    "New Orleans Pelicans":0x0C2340,"New York Knicks":0x006BB6,"Oklahoma City Thunder":0x007AC1,
    "Orlando Magic":0x0077C0,"Philadelphia 76ers":0x006BB6,"Phoenix Suns":0x1D1160,
    "Portland Trail Blazers":0xE03A3E,"Sacramento Kings":0x5A2D81,"San Antonio Spurs":0xBABABB,
    "Toronto Raptors":0xCE1141,"Utah Jazz":0x002B5C,"Washington Wizards":0x002B5C,
}

TEAM_LOGOS = {
    "ATL":"https://cdn.nba.com/logos/nba/1610612737/global/L/logo.svg",
    "BOS":"https://cdn.nba.com/logos/nba/1610612738/global/L/logo.svg",
    "BKN":"https://cdn.nba.com/logos/nba/1610612751/global/L/logo.svg",
    "CHA":"https://cdn.nba.com/logos/nba/1610612766/global/L/logo.svg",
    "CHI":"https://cdn.nba.com/logos/nba/1610612741/global/L/logo.svg",
    "CLE":"https://cdn.nba.com/logos/nba/1610612739/global/L/logo.svg",
    "DAL":"https://cdn.nba.com/logos/nba/1610612742/global/L/logo.svg",
    "DEN":"https://cdn.nba.com/logos/nba/1610612743/global/L/logo.svg",
    "DET":"https://cdn.nba.com/logos/nba/1610612765/global/L/logo.svg",
    "GSW":"https://cdn.nba.com/logos/nba/1610612744/global/L/logo.svg",
    "HOU":"https://cdn.nba.com/logos/nba/1610612745/global/L/logo.svg",
    "IND":"https://cdn.nba.com/logos/nba/1610612754/global/L/logo.svg",
    "LAC":"https://cdn.nba.com/logos/nba/1610612746/global/L/logo.svg",
    "LAL":"https://cdn.nba.com/logos/nba/1610612747/global/L/logo.svg",
    "MEM":"https://cdn.nba.com/logos/nba/1610612763/global/L/logo.svg",
    "MIA":"https://cdn.nba.com/logos/nba/1610612748/global/L/logo.svg",
    "MIL":"https://cdn.nba.com/logos/nba/1610612749/global/L/logo.svg",
    "MIN":"https://cdn.nba.com/logos/nba/1610612750/global/L/logo.svg",
    "NOP":"https://cdn.nba.com/logos/nba/1610612740/global/L/logo.svg",
    "NYK":"https://cdn.nba.com/logos/nba/1610612752/global/L/logo.svg",
    "OKC":"https://cdn.nba.com/logos/nba/1610612760/global/L/logo.svg",
    "ORL":"https://cdn.nba.com/logos/nba/1610612753/global/L/logo.svg",
    "PHI":"https://cdn.nba.com/logos/nba/1610612755/global/L/logo.svg",
    "PHX":"https://cdn.nba.com/logos/nba/1610612756/global/L/logo.svg",
    "POR":"https://cdn.nba.com/logos/nba/1610612757/global/L/logo.svg",
    "SAC":"https://cdn.nba.com/logos/nba/1610612758/global/L/logo.svg",
    "SAS":"https://cdn.nba.com/logos/nba/1610612759/global/L/logo.svg",
    "TOR":"https://cdn.nba.com/logos/nba/1610612761/global/L/logo.svg",
    "UTA":"https://cdn.nba.com/logos/nba/1610612762/global/L/logo.svg",
    "WAS":"https://cdn.nba.com/logos/nba/1610612764/global/L/logo.svg",
}

WEST = {"GSW","LAC","LAL","PHX","SAC","DEN","OKC","UTA","MIN","DAL","MEM","NOP","POR","HOU","SAS"}
EAST = {"ATL","BOS","BKN","CHA","CHI","CLE","DET","IND","MIA","MIL","NYK","ORL","PHI","TOR","WAS"}

NBA_BANNER = "https://cdn.nba.com/manage/2021/10/nba-75-logo.png"

# ── HTTP helper ───────────────────────────────────────────────────────────────

async def _get(endpoint: str, params: dict = None) -> Optional[dict]:
    try:
        headers = {"Authorization": KEY}
        async with aiohttp.ClientSession(headers=headers) as s:
            async with s.get(f"{BASE}{endpoint}", params=params,
                             timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200:
                    return await r.json()
                print(f"[API] {endpoint} → HTTP {r.status}")
    except Exception as e:
        print(f"[API] {endpoint}: {e}")
    return None

# ── Public API calls ──────────────────────────────────────────────────────────

async def get_standings() -> list:
    d = await _get("/standings", {"season": 2024})
    return d.get("data", []) if d else []

async def get_games_for_date(dt: date) -> list:
    d = await _get("/games", {"dates[]": dt.isoformat(), "per_page": 30})
    return d.get("data", []) if d else []

async def get_today_games() -> list:
    return await get_games_for_date(date.today())

async def get_live_games() -> list:
    d = await _get("/games/live")
    return d.get("data", []) if d else []

async def get_game_stats(game_id: int) -> list:
    d = await _get("/stats", {"game_ids[]": game_id, "per_page": 100})
    return d.get("data", []) if d else []

async def get_week_games() -> list:
    """Returns games for the next 7 days."""
    games = []
    today = date.today()
    for i in range(7):
        day = today + timedelta(days=i)
        day_games = await get_games_for_date(day)
        for g in day_games:
            g["_date"] = day.isoformat()
        games.extend(day_games)
    return games

# ── Helpers ───────────────────────────────────────────────────────────────────

def emoji(name: str) -> str:
    return TEAM_EMOJIS.get(name, "🏀")

def color(name: str) -> int:
    return TEAM_COLORS.get(name, 0xE8174B)

def logo(abbr: str) -> str:
    return TEAM_LOGOS.get(abbr, "https://cdn.nba.com/logos/leagues/logo-nba.svg")

def conference(abbr: str) -> str:
    if abbr in WEST: return "West"
    if abbr in EAST: return "East"
    return "?"
