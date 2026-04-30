import discord
from datetime import datetime, date
from utils.nba_api import emoji, color, logo, team_name

NBA_RED  = 0xE8174B
NBA_BLUE = 0x17408B
NBA_GOLD = 0xC9A227

DAYS_FR = {
    "Monday":"Lundi","Tuesday":"Mardi","Wednesday":"Mercredi",
    "Thursday":"Jeudi","Friday":"Vendredi","Saturday":"Samedi","Sunday":"Dimanche"
}

# ── WEEKLY SCHEDULE ───────────────────────────────────────────────────────────

def build_weekly_embeds(schedule: dict[str, list]) -> list[discord.Embed]:
    header = discord.Embed(
        title="🗓️  NBA — Programme de la Semaine",
        color=NBA_RED,
        timestamp=datetime.utcnow(),
    )
    header.set_thumbnail(url="https://cdn.nba.com/logos/leagues/logo-nba.svg")
    header.set_footer(text="NBA Bot Premium • Programme Hebdomadaire")

    total = sum(len(v) for v in schedule.values())
    days_str = list(schedule.keys())
    if days_str:
        header.description = (
            f"**Du {days_str[0]}  au  {days_str[-1]}**\n"
            f"**{total} match(s) au programme**\n"
            f"{'━'*36}"
        )

    embeds = [header]

    for day_iso, games in schedule.items():
        if not games:
            continue
        dt     = datetime.strptime(day_iso, "%Y-%m-%d")
        day_fr = DAYS_FR.get(dt.strftime("%A"), dt.strftime("%A"))
        label  = f"{day_fr} **{dt.strftime('%d/%m')}**"

        lines = []
        for g in games:
            h_abbr = g["home_abbr"]
            a_abbr = g["away_abbr"]
            status = g.get("status","")
            playoff = g.get("series_text","")
            playoff_txt = f" `{playoff}`" if playoff else ""
            lines.append(
                f"{emoji(a_abbr)} **{a_abbr}** `{g['away_name']}`  ⚔️  "
                f"{emoji(h_abbr)} **{h_abbr}** `{g['home_name']}`"
                f"  —  `{status}`{playoff_txt}"
            )

        embed = discord.Embed(
            title=f"📅  {label}  —  {len(games)} match{'s' if len(games)>1 else ''}",
            description="\n".join(lines),
            color=NBA_BLUE,
        )
        embeds.append(embed)

    return embeds

# ── GAME ANNOUNCEMENT ─────────────────────────────────────────────────────────

def build_game_announcement(game: dict) -> discord.Embed:
    h = game["home_abbr"]
    a = game["away_abbr"]
    playoff = game.get("series_text","")

    embed = discord.Embed(
        title="🏀  MATCH DU JOUR — TONIGHT",
        description=(
            f"## {emoji(a)}  {game['away_city']} {game['away_name']}"
            + (f"  `{game['away_record']}`" if game.get("away_record") else "")
            + f"\n# ⚔️  VS\n"
            f"## {emoji(h)}  {game['home_city']} {game['home_name']}"
            + (f"  `{game['home_record']}`" if game.get("home_record") else "")
            + (f"\n\n> 🏆 **{playoff}**" if playoff else "")
            + f"\n\n> 🕐 **{game['status']}**"
            + (f"\n> 🏟️ **{game['arena']}**" if game.get("arena") else "")
        ),
        color=NBA_RED,
        timestamp=datetime.utcnow(),
    )
    embed.set_thumbnail(url=logo(h))
    embed.set_footer(text="NBA Bot Premium • Game Day 🏀")
    return embed

# ── LIVE SCORE ────────────────────────────────────────────────────────────────

def build_live_score(game: dict) -> discord.Embed:
    h      = game["home_abbr"]
    a      = game["away_abbr"]
    h_s    = game["home_score"]
    a_s    = game["away_score"]
    code   = game["status_code"]   # 1=scheduled 2=live 3=final
    status = game["status"]
    period = game.get("period", 0)
    clock  = game.get("clock", "")
    playoff = game.get("series_text","")

    is_live  = code == 2
    is_final = code == 3

    clr   = 0x00FF88 if is_live else (NBA_GOLD if is_final else NBA_BLUE)
    phase = f"🔴 LIVE Q{period} {clock}" if is_live else ("🏁 FINAL" if is_final else f"🕐 {status}")

    desc_lines = [
        f"{'🏆 ' if is_final and a_s > h_s else ''}{emoji(a)}  **{game['away_city']} {game['away_name']}**"
        + (f"  `{game['away_record']}`" if game.get("away_record") else ""),
        f"# {a_s}",
        "",
        f"{'🏆 ' if is_final and h_s > a_s else ''}{emoji(h)}  **{game['home_city']} {game['home_name']}**"
        + (f"  `{game['home_record']}`" if game.get("home_record") else ""),
        f"# {h_s}",
    ]

    if playoff:
        desc_lines.append(f"\n> 🏆 **{playoff}**")

    embed = discord.Embed(title=phase, description="\n".join(desc_lines), color=clr, timestamp=datetime.utcnow())
    embed.set_thumbnail(url=logo(h))
    embed.set_footer(text="NBA Bot Premium • Live Score")
    return embed

# ── BOXSCORE ──────────────────────────────────────────────────────────────────

def build_boxscore(game: dict, bs: dict) -> list[discord.Embed]:
    h      = game["home_abbr"]
    a      = game["away_abbr"]
    h_s    = game["home_score"]
    a_s    = game["away_score"]
    winner_abbr  = h if h_s > a_s else a
    loser_abbr   = a if h_s > a_s else h
    w_name = f"{game['home_city']} {game['home_name']}" if h_s > a_s else f"{game['away_city']} {game['away_name']}"
    l_name = f"{game['away_city']} {game['away_name']}" if h_s > a_s else f"{game['home_city']} {game['home_name']}"
    diff   = abs(h_s - a_s)
    playoff = game.get("series_text","")

    header = discord.Embed(
        title=f"📊  FIN DE MATCH  —  {a} @ {h}",
        description=(
            f"## 🏆 {emoji(winner_abbr)}  {w_name}  **GAGNE**\n"
            f"# {emoji(a)}  {a_s}   —   {h_s}  {emoji(h)}\n"
            f"*Défaite de {emoji(loser_abbr)} {l_name}  •  écart : **+{diff} pts***"
            + (f"\n\n> 🏆 **{playoff}**" if playoff else "")
        ),
        color=color(winner_abbr),
        timestamp=datetime.utcnow(),
    )
    header.set_thumbnail(url=logo(winner_abbr))
    header.set_footer(text="NBA Bot Premium • Feuille de Match Officielle")
    embeds = [header]

    # Stats tables
    for side_key, abbr, city, nm in [
        ("away", a, game["away_city"], game["away_name"]),
        ("home", h, game["home_city"], game["home_name"]),
    ]:
        players = bs.get(side_key, []) if bs else []
        players.sort(key=lambda x: x["pts"], reverse=True)

        if not players:
            continue

        rows = ["```"]
        rows.append(f"{'JOUEUR':<20} {'MIN':>5} {'PTS':>4} {'REB':>4} {'PD':>4} {'INT':>4} {'CT':>4} {'TM':>5} {'3P':>4}")
        rows.append("─" * 58)
        for p in players[:10]:
            nm2  = p["name"][:18]
            rows.append(
                f"{nm2:<20} {p['min']:>5} {p['pts']:>4} {p['reb']:>4} "
                f"{p['ast']:>4} {p['stl']:>4} {p['blk']:>4} "
                f"{p['fgm']}/{p['fga']:>3} {p['tpm']:>4}"
            )
        rows.append("```")
        rows.append("*MIN=Minutes PTS=Points REB=Rebonds PD=Passes INT=Interceptions CT=Contres TM=Tirs 3P=3pts*")

        e = discord.Embed(
            title=f"{emoji(abbr)}  {city} {nm}",
            description="\n".join(rows),
            color=color(abbr),
        )
        e.set_thumbnail(url=logo(abbr))
        embeds.append(e)

    return embeds

# ── STANDINGS ─────────────────────────────────────────────────────────────────

def build_standings_embed(teams: list, conference: str) -> discord.Embed:
    is_west = conference == "West"
    label   = "🌅  WESTERN CONFERENCE" if is_west else "🌆  EASTERN CONFERENCE"
    clr     = 0xC8102E if is_west else 0x1D428A

    embed = discord.Embed(
        title=f"🏆  NBA STANDINGS — {label}",
        color=clr,
        timestamp=datetime.utcnow(),
    )
    embed.set_thumbnail(url="https://cdn.nba.com/logos/leagues/logo-nba.svg")
    embed.set_footer(text="NBA Bot Premium • Classement mis à jour en temps réel")

    if not teams:
        embed.description = "> Aucune donnée disponible."
        return embed

    lines = []
    for i, t in enumerate(teams):
        abbr   = t["abbr"]
        w      = t["wins"]
        l      = t["losses"]
        pct    = f"{float(t['pct']):.3f}"
        gb     = t["gb"] or "-"
        streak = t["streak"]
        l10    = t["l10"]

        # Rank badge
        if i == 0:   badge = "🥇"
        elif i == 1: badge = "🥈"
        elif i == 2: badge = "🥉"
        elif i < 6:  badge = "✦"
        elif i < 10: badge = "◈"
        else:        badge = "✖"

        # Streak indicator
        streak_icon = ""
        if streak:
            n = ''.join(filter(str.isdigit, streak))
            if "W" in streak:
                streak_icon = f"🔥{n}"
            else:
                streak_icon = f"❄️{n}"

        clinch = t.get("clinch","")
        clinch_icon = " `✦`" if clinch and clinch != "-" else ""

        lines.append(
            f"{badge} **#{i+1}** {emoji(abbr)} `{abbr}` **{w}W-{l}L** "
            f"`{pct}` GB:{gb} L10:{l10} {streak_icon}{clinch_icon}"
        )

        if i == 5:
            lines.append("━━━━━━━━━━━ 🎟️ Play-In ↓")
        elif i == 9:
            lines.append("━━━━━━━━━━━ ✖ Éliminé ↓")

    embed.description = "\n".join(lines)
    embed.add_field(
        name="Légende",
        value="🥇🥈🥉 Top 3  •  ✦ Playoff direct (6 équipes)  •  ◈ Play-In (4 équipes)\n🔥 Win streak  •  ❄️ Lose streak  •  GB = Games Behind",
        inline=False,
    )
    return embed

# ── NEWS EMBED ────────────────────────────────────────────────────────────────

CAT_EMOJI  = {"injury":"🏥","trade":"🔄","draft":"📋","exploit":"🌟","news":"📰"}
CAT_LABEL  = {"injury":"BLESSURE / RETOUR","trade":"TRANSFERT / TRADE","draft":"DRAFT","exploit":"EXPLOIT","news":"ACTUALITÉ NBA"}
CAT_COLOR  = {"injury":0xFF6B35,"trade":0xC9A227,"draft":0x00B4D8,"exploit":0xFFD700,"news":0xE8174B}

def build_news_embed(title: str, summary: str, source: str,
                     image_url: str|None, category: str, published: str="") -> discord.Embed:
    cat_e = CAT_EMOJI.get(category,"📰")
    cat_l = CAT_LABEL.get(category,"ACTUALITÉ NBA")
    clr   = CAT_COLOR.get(category, NBA_RED)

    embed = discord.Embed(
        title=f"{cat_e}  {title}",
        description=f">>> {summary}",
        color=clr,
        timestamp=datetime.utcnow(),
    )
    embed.set_author(
        name=f"NBA • {cat_l}",
        icon_url="https://cdn.nba.com/logos/leagues/logo-nba.svg",
    )
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text=f"Source : {source}" + (f"  •  {published[:10]}" if published else ""))
    return embed