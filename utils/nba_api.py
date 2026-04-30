"""
NBA Stats API — stats.nba.com
Gratuit, sans clé API, données officielles en temps réel.
"""
import aiohttp
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional

# ── NBA Stats API headers (required to avoid 403) ────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":    "https://www.nba.com/",
    "Origin":     "https://www.nba.com",
    "Accept":     "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token":  "true",
}

BASE_STATS = "https://stats.nba.com/stats"
BASE_DATA  = "https://cdn.nba.com/static/json"
SCORE_URL  = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
SCHED_URL  = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"

# ── Static team data ──────────────────────────────────────────────────────────

TEAMS = {
    1610612737: {"name":"Atlanta Hawks",        "abbr":"ATL","conf":"East"},
    1610612738: {"name":"Boston Celtics",        "abbr":"BOS","conf":"East"},
    1610612751: {"name":"Brooklyn Nets",         "abbr":"BKN","conf":"East"},
    1610612766: {"name":"Charlotte Hornets",     "abbr":"CHA","conf":"East"},
    1610612741: {"name":"Chicago Bulls",         "abbr":"CHI","conf":"East"},
    1610612739: {"name":"Cleveland Cavaliers",   "abbr":"CLE","conf":"East"},
    1610612742: {"name":"Dallas Mavericks",      "abbr":"DAL","conf":"West"},
    1610612743: {"name":"Denver Nuggets",        "abbr":"DEN","conf":"West"},
    1610612765: {"name":"Detroit Pistons",       "abbr":"DET","conf":"East"},
    1610612744: {"name":"Golden State Warriors", "abbr":"GSW","conf":"West"},
    1610612745: {"name":"Houston Rockets",       "abbr":"HOU","conf":"West"},
    1610612754: {"name":"Indiana Pacers",        "abbr":"IND","conf":"East"},
    1610612746: {"name":"LA Clippers",           "abbr":"LAC","conf":"West"},
    1610612747: {"name":"Los Angeles Lakers",    "abbr":"LAL","conf":"West"},
    1610612763: {"name":"Memphis Grizzlies",     "abbr":"MEM","conf":"West"},
    1610612748: {"name":"Miami Heat",            "abbr":"MIA","conf":"East"},
    1610612749: {"name":"Milwaukee Bucks",       "abbr":"MIL","conf":"East"},
    1610612750: {"name":"Minnesota Timberwolves","abbr":"MIN","conf":"West"},
    1610612740: {"name":"New Orleans Pelicans",  "abbr":"NOP","conf":"West"},
    1610612752: {"name":"New York Knicks",       "abbr":"NYK","conf":"East"},
    1610612760: {"name":"Oklahoma City Thunder", "abbr":"OKC","conf":"West"},
    1610612753: {"name":"Orlando Magic",         "abbr":"ORL","conf":"East"},
    1610612755: {"name":"Philadelphia 76ers",    "abbr":"PHI","conf":"East"},
    1610612756: {"name":"Phoenix Suns",          "abbr":"PHX","conf":"West"},
    1610612757: {"name":"Portland Trail Blazers","abbr":"POR","conf":"West"},
    1610612758: {"name":"Sacramento Kings",      "abbr":"SAC","conf":"West"},
    1610612759: {"name":"San Antonio Spurs",     "abbr":"SAS","conf":"West"},
    1610612761: {"name":"Toronto Raptors",       "abbr":"TOR","conf":"East"},
    1610612762: {"name":"Utah Jazz",             "abbr":"UTA","conf":"West"},
    1610612764: {"name":"Washington Wizards",    "abbr":"WAS","conf":"East"},
}

TEAM_BY_ABBR = {v["abbr"]: {**v, "id": k} for k, v in TEAMS.items()}

TEAM_COLORS = {
    "ATL":0xE03A3E,"BOS":0x007A33,"BKN":0x111111,"CHA":0x1D1160,"CHI":0xCE1141,
    "CLE":0x860038,"DAL":0x00538C,"DEN":0x0E2240,"DET":0xC8102E,"GSW":0x1D428A,
    "HOU":0xCE1141,"IND":0x002D62,"LAC":0xC8102E,"LAL":0x552583,"MEM":0x5D76A9,
    "MIA":0x98002E,"MIL":0x00471B,"MIN":0x0C2340,"NOP":0x0C2340,"NYK":0x006BB6,
    "OKC":0x007AC1,"ORL":0x0077C0,"PHI":0x006BB6,"PHX":0x1D1160,"POR":0xE03A3E,
    "SAC":0x5A2D81,"SAS":0xBABABB,"TOR":0xCE1141,"UTA":0x002B5C,"WAS":0x002B5C,
}

TEAM_LOGOS = {
    abbr: f"https://cdn.nba.com/logos/nba/{tid}/global/L/logo.svg"
    for tid, d in TEAMS.items() for abbr in [d["abbr"]]
}

def color(abbr: str) -> int:
    return TEAM_COLORS.get(abbr, 0xE8174B)

def logo(abbr: str) -> str:
    tid = TEAM_BY_ABBR.get(abbr, {}).get("id", 0)
    return f"https://cdn.nba.com/logos/nba/{tid}/global/L/logo.svg"

def team_name(abbr: str) -> str:
    return TEAM_BY_ABBR.get(abbr, {}).get("name", abbr)

def team_conf(abbr: str) -> str:
    return TEAM_BY_ABBR.get(abbr, {}).get("conf", "?")

# ── HTTP helper ───────────────────────────────────────────────────────────────

async def _get(url: str, params: dict = None) -> Optional[dict]:
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(url, params=params,
                             timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    return await r.json(content_type=None)
                print(f"[NBA API] {url} → {r.status}")
    except Exception as e:
        print(f"[NBA API] {url}: {e}")
    return None

# ── TODAY'S SCOREBOARD ────────────────────────────────────────────────────────

async def get_scoreboard() -> list[dict]:
    """Returns today's games with live scores from NBA CDN."""
    data = await _get(SCORE_URL)
    if not data:
        return []
    try:
        games_raw = data["scoreboard"]["games"]
        games = []
        for g in games_raw:
            home_abbr = g["homeTeam"]["teamTricode"]
            away_abbr = g["awayTeam"]["teamTricode"]
            games.append({
                "id":           g["gameId"],
                "status":       g["gameStatusText"].strip(),
                "status_code":  g["gameStatus"],   # 1=scheduled 2=live 3=final
                "period":       g.get("period", 0),
                "clock":        g.get("gameClock", ""),
                "home_abbr":    home_abbr,
                "home_name":    g["homeTeam"]["teamName"],
                "home_city":    g["homeTeam"]["teamCity"],
                "home_score":   g["homeTeam"]["score"],
                "home_record":  f"{g['homeTeam']['wins']}-{g['homeTeam']['losses']}",
                "away_abbr":    away_abbr,
                "away_name":    g["awayTeam"]["teamName"],
                "away_city":    g["awayTeam"]["teamCity"],
                "away_score":   g["awayTeam"]["score"],
                "away_record":  f"{g['awayTeam']['wins']}-{g['awayTeam']['losses']}",
                "arena":        g.get("arena", {}).get("arenaName", ""),
                "series_text":  g.get("seriesText", ""),
                "playoff":      bool(g.get("seriesText", "")),
            })
        return games
    except Exception as e:
        print(f"[Scoreboard] parse error: {e}")
        return []

# ── BOXSCORE ──────────────────────────────────────────────────────────────────

async def get_boxscore(game_id: str) -> Optional[dict]:
    """Returns full boxscore for a finished/live game."""
    url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
    data = await _get(url)
    if not data:
        return None
    try:
        bs = data["game"]
        result = {"home": [], "away": []}
        for side in ["homeTeam", "awayTeam"]:
            key = "home" if side == "homeTeam" else "away"
            for p in bs[side]["players"]:
                s = p.get("statistics", {})
                if s.get("secondsPlayed", 0) == 0:
                    continue
                result[key].append({
                    "name":   f"{p['name']}",
                    "pts":    s.get("points", 0),
                    "reb":    s.get("reboundsTotal", 0),
                    "ast":    s.get("assists", 0),
                    "stl":    s.get("steals", 0),
                    "blk":    s.get("blocks", 0),
                    "fgm":    s.get("fieldGoalsMade", 0),
                    "fga":    s.get("fieldGoalsAttempted", 0),
                    "tpm":    s.get("threePointersMade", 0),
                    "min":    s.get("minutesCalculated", "PT0M").replace("PT","").replace("M","min"),
                })
        return result
    except Exception as e:
        print(f"[Boxscore] parse error: {e}")
        return None

# ── STANDINGS ─────────────────────────────────────────────────────────────────

async def get_standings() -> dict[str, list]:
    """Returns {'West': [...], 'East': [...]} sorted by rank."""
    url = f"{BASE_STATS}/leaguestandingsv3"
    params = {
        "LeagueID": "00",
        "Season": "2024-25",
        "SeasonType": "Playoffs",   # use Playoffs during postseason
    }
    data = await _get(url, params)

    # Fallback to regular season if playoffs returns nothing
    if not data or not data.get("resultSets"):
        params["SeasonType"] = "Regular Season"
        data = await _get(url, params)

    if not data:
        return {"West": [], "East": []}

    try:
        rs = data["resultSets"][0]
        headers = rs["headers"]
        rows    = rs["rowSet"]
        idx = {h: i for i, h in enumerate(headers)}

        west, east = [], []
        for row in rows:
            conf = row[idx["Conference"]]
            team = {
                "rank":    row[idx["PlayoffRank"]] if "PlayoffRank" in idx else row[idx["ConferenceRank"]],
                "name":    row[idx["TeamName"]],
                "city":    row[idx["TeamCity"]],
                "abbr":    row[idx["TeamAbbreviation"]],
                "wins":    row[idx["WINS"]],
                "losses":  row[idx["LOSSES"]],
                "pct":     row[idx["WinPCT"]],
                "gb":      row[idx["ConferenceGamesBack"]],
                "home":    row[idx["HOME"]],
                "road":    row[idx["ROAD"]],
                "l10":     row[idx["L10"]],
                "streak":  row[idx["strCurrentStreak"]],
                "clinch":  row[idx.get("clinchIndicator", -1)] if "clinchIndicator" in idx else "",
            }
            if conf == "West":
                west.append(team)
            else:
                east.append(team)

        west.sort(key=lambda x: x["rank"])
        east.sort(key=lambda x: x["rank"])
        return {"West": west, "East": east}
    except Exception as e:
        print(f"[Standings] parse error: {e}")
        return {"West": [], "East": []}

# ── WEEKLY SCHEDULE ───────────────────────────────────────────────────────────

async def get_week_schedule() -> dict[str, list]:
    """Returns games for today + next 6 days grouped by date."""
    url = f"{BASE_STATS}/scoreboard"
    result: dict[str, list] = {}
    today = date.today()

    for i in range(7):
        day = today + timedelta(days=i)
        day_str = day.strftime("%m/%d/%Y")
        params = {"GameDate": day_str, "LeagueID": "00", "DayOffset": "0"}
        data = await _get(url, params)
        games = []
        if data:
            try:
                rs = data["resultSets"]
                # GameHeader is index 0
                gh = rs[0]
                hdrs = {h: i for i, h in enumerate(gh["headers"])}
                for row in gh["rowSet"]:
                    home_abbr = row[hdrs.get("HOME_TEAM_ID", 0)]
                    away_abbr = row[hdrs.get("VISITOR_TEAM_ID", 0)]
                    # Convert team IDs to abbr
                    home_info = TEAMS.get(home_abbr, {})
                    away_info = TEAMS.get(away_abbr, {})
                    games.append({
                        "id":         row[hdrs["GAME_ID"]],
                        "status":     row[hdrs["GAME_STATUS_TEXT"]].strip(),
                        "home_abbr":  home_info.get("abbr","?"),
                        "home_name":  home_info.get("name","?"),
                        "away_abbr":  away_info.get("abbr","?"),
                        "away_name":  away_info.get("name","?"),
                        "arena":      row[hdrs.get("ARENA_NAME","")],
                    })
            except Exception as e:
                print(f"[Schedule {day}] parse error: {e}")
        result[day.isoformat()] = games
        await asyncio.sleep(0.3)   # be polite to the API

    return result