"""
NBA official APIs — stats.nba.com + cdn.nba.com
Gratuit, sans clé, données officielles.
"""
import aiohttp
import asyncio
from datetime import date, datetime, timedelta
from typing import Optional

HEADERS = {
    "User-Agent":           "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120",
    "Referer":              "https://www.nba.com/",
    "Origin":               "https://www.nba.com",
    "Accept":               "application/json, text/plain, */*",
    "Accept-Language":      "en-US,en;q=0.9",
    "x-nba-stats-origin":   "stats",
    "x-nba-stats-token":    "true",
}

CDN_SCOREBOARD = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
STATS_BASE     = "https://stats.nba.com/stats"

# ── Team registry ─────────────────────────────────────────────────────────────

TEAMS = {
    1610612737: {"name":"Atlanta Hawks",         "abbr":"ATL","conf":"East"},
    1610612738: {"name":"Boston Celtics",         "abbr":"BOS","conf":"East"},
    1610612751: {"name":"Brooklyn Nets",          "abbr":"BKN","conf":"East"},
    1610612766: {"name":"Charlotte Hornets",      "abbr":"CHA","conf":"East"},
    1610612741: {"name":"Chicago Bulls",          "abbr":"CHI","conf":"East"},
    1610612739: {"name":"Cleveland Cavaliers",    "abbr":"CLE","conf":"East"},
    1610612742: {"name":"Dallas Mavericks",       "abbr":"DAL","conf":"West"},
    1610612743: {"name":"Denver Nuggets",         "abbr":"DEN","conf":"West"},
    1610612765: {"name":"Detroit Pistons",        "abbr":"DET","conf":"East"},
    1610612744: {"name":"Golden State Warriors",  "abbr":"GSW","conf":"West"},
    1610612745: {"name":"Houston Rockets",        "abbr":"HOU","conf":"West"},
    1610612754: {"name":"Indiana Pacers",         "abbr":"IND","conf":"East"},
    1610612746: {"name":"LA Clippers",            "abbr":"LAC","conf":"West"},
    1610612747: {"name":"Los Angeles Lakers",     "abbr":"LAL","conf":"West"},
    1610612763: {"name":"Memphis Grizzlies",      "abbr":"MEM","conf":"West"},
    1610612748: {"name":"Miami Heat",             "abbr":"MIA","conf":"East"},
    1610612749: {"name":"Milwaukee Bucks",        "abbr":"MIL","conf":"East"},
    1610612750: {"name":"Minnesota Timberwolves", "abbr":"MIN","conf":"West"},
    1610612740: {"name":"New Orleans Pelicans",   "abbr":"NOP","conf":"West"},
    1610612752: {"name":"New York Knicks",        "abbr":"NYK","conf":"East"},
    1610612760: {"name":"Oklahoma City Thunder",  "abbr":"OKC","conf":"West"},
    1610612753: {"name":"Orlando Magic",          "abbr":"ORL","conf":"East"},
    1610612755: {"name":"Philadelphia 76ers",     "abbr":"PHI","conf":"East"},
    1610612756: {"name":"Phoenix Suns",           "abbr":"PHX","conf":"West"},
    1610612757: {"name":"Portland Trail Blazers", "abbr":"POR","conf":"West"},
    1610612758: {"name":"Sacramento Kings",       "abbr":"SAC","conf":"West"},
    1610612759: {"name":"San Antonio Spurs",      "abbr":"SAS","conf":"West"},
    1610612761: {"name":"Toronto Raptors",        "abbr":"TOR","conf":"East"},
    1610612762: {"name":"Utah Jazz",              "abbr":"UTA","conf":"West"},
    1610612764: {"name":"Washington Wizards",     "abbr":"WAS","conf":"East"},
}

ABBR_TO_ID = {v["abbr"]: k for k, v in TEAMS.items()}

def team_logo(abbr: str) -> str:
    tid = ABBR_TO_ID.get(abbr.upper(), 0)
    return f"https://cdn.nba.com/logos/nba/{tid}/global/L/logo.svg"

def team_name(abbr: str) -> str:
    tid = ABBR_TO_ID.get(abbr.upper(), 0)
    return TEAMS.get(tid, {}).get("name", abbr)

def team_conf(abbr: str) -> str:
    tid = ABBR_TO_ID.get(abbr.upper(), 0)
    return TEAMS.get(tid, {}).get("conf", "?")

TEAM_COLORS = {
    "ATL":0xE03A3E,"BOS":0x007A33,"BKN":0x111111,"CHA":0x1D1160,"CHI":0xCE1141,
    "CLE":0x860038,"DAL":0x00538C,"DEN":0x0E2240,"DET":0xC8102E,"GSW":0x1D428A,
    "HOU":0xCE1141,"IND":0x002D62,"LAC":0xC8102E,"LAL":0x552583,"MEM":0x5D76A9,
    "MIA":0x98002E,"MIL":0x00471B,"MIN":0x0C2340,"NOP":0x0C2340,"NYK":0x006BB6,
    "OKC":0x007AC1,"ORL":0x0077C0,"PHI":0x006BB6,"PHX":0x1D1160,"POR":0xE03A3E,
    "SAC":0x5A2D81,"SAS":0x000000,"TOR":0xCE1141,"UTA":0x002B5C,"WAS":0x002B5C,
}

def team_color(abbr: str) -> int:
    return TEAM_COLORS.get(abbr.upper(), 0xE8174B)

# ── HTTP ──────────────────────────────────────────────────────────────────────

async def _get(url: str, params: dict = None) -> Optional[dict]:
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as s:
            async with s.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    return await r.json(content_type=None)
                print(f"[NBA] {url} → {r.status}")
    except Exception as e:
        print(f"[NBA] error {url}: {e}")
    return None

# ── SCOREBOARD (today) ────────────────────────────────────────────────────────

async def get_scoreboard() -> list[dict]:
    data = await _get(CDN_SCOREBOARD)
    if not data:
        return []
    try:
        out = []
        for g in data["scoreboard"]["games"]:
            h = g["homeTeam"]
            a = g["awayTeam"]
            out.append({
                "id":           g["gameId"],
                "status_code":  g["gameStatus"],      # 1=scheduled 2=live 3=final
                "status_text":  g["gameStatusText"].strip(),
                "period":       g.get("period", 0),
                "clock":        g.get("gameClock", ""),
                "home_abbr":    h["teamTricode"],
                "home_name":    f"{h['teamCity']} {h['teamName']}",
                "home_score":   h["score"],
                "home_record":  f"{h['wins']}-{h['losses']}",
                "away_abbr":    a["teamTricode"],
                "away_name":    f"{a['teamCity']} {a['teamName']}",
                "away_score":   a["score"],
                "away_record":  f"{a['wins']}-{a['losses']}",
                "arena":        g.get("arena", {}).get("arenaName", ""),
                "series":       g.get("seriesText", ""),   # Playoff info e.g. "LAL leads 3-2"
            })
        return out
    except Exception as e:
        print(f"[Scoreboard] parse: {e}")
        return []

# ── BOXSCORE ──────────────────────────────────────────────────────────────────

async def get_boxscore(game_id: str) -> Optional[dict]:
    url  = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
    data = await _get(url)
    if not data:
        return None
    try:
        result = {}
        for side in ["homeTeam","awayTeam"]:
            key = "home" if side == "homeTeam" else "away"
            players = []
            for p in data["game"][side]["players"]:
                s = p.get("statistics", {})
                if (s.get("secondsPlayed") or 0) == 0:
                    continue
                players.append({
                    "name": p.get("name","?"),
                    "pts":  s.get("points", 0),
                    "reb":  s.get("reboundsTotal", 0),
                    "ast":  s.get("assists", 0),
                    "stl":  s.get("steals", 0),
                    "blk":  s.get("blocks", 0),
                    "fgm":  s.get("fieldGoalsMade", 0),
                    "fga":  s.get("fieldGoalsAttempted", 0),
                    "tpm":  s.get("threePointersMade", 0),
                    "min":  s.get("minutesCalculated","PT0M").replace("PT","").replace("M","min"),
                })
            players.sort(key=lambda x: x["pts"], reverse=True)
            result[key] = players
        return result
    except Exception as e:
        print(f"[Boxscore] parse: {e}")
        return None

# ── STANDINGS ─────────────────────────────────────────────────────────────────

async def get_standings_regular() -> dict:
    """Regular season standings."""
    return await _fetch_standings("Regular Season")

async def get_standings_playoff() -> dict:
    """Playoff standings (bracket info)."""
    return await _fetch_standings("Playoffs")

async def get_standings_playin() -> dict:
    """Play-In tournament standings."""
    return await _fetch_standings("PlayIn")

async def _fetch_standings(season_type: str) -> dict:
    url = f"{STATS_BASE}/leaguestandingsv3"
    params = {
        "LeagueID":  "00",
        "Season":    "2024-25",
        "SeasonType": season_type,
    }
    data = await _get(url, params)
    if not data or not data.get("resultSets"):
        return {"West": [], "East": []}

    try:
        rs      = data["resultSets"][0]
        headers = rs["headers"]
        rows    = rs["rowSet"]
        idx     = {h: i for i, h in enumerate(headers)}

        west, east = [], []
        for row in rows:
            conf = row[idx["Conference"]]
            # Try PlayoffRank first, then ConferenceRank
            rank_key = "PlayoffRank" if "PlayoffRank" in idx else "ConferenceRank"
            t = {
                "rank":   row[idx[rank_key]],
                "abbr":   row[idx["TeamAbbreviation"]],
                "name":   f"{row[idx['TeamCity']]} {row[idx['TeamName']]}",
                "wins":   row[idx["WINS"]],
                "losses": row[idx["LOSSES"]],
                "pct":    float(row[idx["WinPCT"]] or 0),
                "gb":     row[idx["ConferenceGamesBack"]] or "-",
                "l10":    row[idx["L10"]],
                "streak": row[idx["strCurrentStreak"]],
                "home":   row[idx["HOME"]],
                "road":   row[idx["ROAD"]],
            }
            if conf == "West":
                west.append(t)
            else:
                east.append(t)

        west.sort(key=lambda x: x["rank"])
        east.sort(key=lambda x: x["rank"])
        return {"West": west, "East": east}

    except Exception as e:
        print(f"[Standings {season_type}] parse: {e}")
        return {"West": [], "East": []}

# ── WEEK SCHEDULE ─────────────────────────────────────────────────────────────

async def get_week_schedule() -> dict[str, list]:
    """Games for today + 6 days, grouped by date string."""
    result: dict[str, list] = {}
    today = date.today()

    for i in range(7):
        day     = today + timedelta(days=i)
        day_iso = day.isoformat()
        day_str = day.strftime("%m/%d/%Y")

        data = await _get(f"{STATS_BASE}/scoreboard", {
            "GameDate": day_str, "LeagueID": "00", "DayOffset": "0"
        })
        games = []
        if data and data.get("resultSets"):
            try:
                gh   = data["resultSets"][0]
                hdrs = {h: i for i, h in enumerate(gh["headers"])}
                ls   = data["resultSets"][1]   # LineScore
                ls_hdrs = {h: i for i, h in enumerate(ls["headers"])}
                ls_rows  = ls["rowSet"]

                for row in gh["rowSet"]:
                    gid = row[hdrs["GAME_ID"]]
                    # Find home/away from LineScore
                    ls_game = [r for r in ls_rows if r[ls_hdrs["GAME_ID"]] == gid]
                    home_abbr = away_abbr = "?"
                    if len(ls_game) >= 2:
                        home_abbr = ls_game[1][ls_hdrs["TEAM_ABBREVIATION"]]
                        away_abbr = ls_game[0][ls_hdrs["TEAM_ABBREVIATION"]]
                    games.append({
                        "id":         gid,
                        "status":     row[hdrs["GAME_STATUS_TEXT"]].strip(),
                        "home_abbr":  home_abbr,
                        "home_name":  team_name(home_abbr),
                        "away_abbr":  away_abbr,
                        "away_name":  team_name(away_abbr),
                    })
            except Exception as e:
                print(f"[Schedule {day_iso}] parse: {e}")

        result[day_iso] = games
        await asyncio.sleep(0.4)

    return result