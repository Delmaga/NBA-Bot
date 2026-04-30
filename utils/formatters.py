import discord
from datetime import datetime, date, timedelta
from utils.nba_api import emoji, color, logo, WEST, EAST, NBA_BANNER

NBA_RED  = 0xE8174B
NBA_BLUE = 0x17408B
NBA_GOLD = 0xC9A227

# ─────────────────────────────────────────────────────────────────────────────
#  WEEKLY SCHEDULE
# ─────────────────────────────────────────────────────────────────────────────

def build_weekly_schedule(games_by_day: dict[str, list]) -> list[discord.Embed]:
    """Returns one embed per day that has games."""
    embeds = []

    header = discord.Embed(
        title="🗓️  NBA — Programme de la Semaine",
        description=(
            f"**Du {list(games_by_day.keys())[0]}  au  {list(games_by_day.keys())[-1]}**\n"
            f"{'━'*36}"
        ),
        color=NBA_RED,
        timestamp=datetime.utcnow(),
    )
    header.set_thumbnail(url="https://cdn.nba.com/logos/leagues/logo-nba.svg")
    header.set_footer(text="NBA Bot Premium • Programme Hebdomadaire")
    embeds.append(header)

    DAYS_FR = {"Monday":"Lundi","Tuesday":"Mardi","Wednesday":"Mercredi",
               "Thursday":"Jeudi","Friday":"Vendredi","Saturday":"Samedi","Sunday":"Dimanche"}

    for day_iso, games in games_by_day.items():
        if not games:
            continue
        dt  = datetime.strptime(day_iso, "%Y-%m-%d")
        day_fr = DAYS_FR.get(dt.strftime("%A"), dt.strftime("%A"))
        day_label = f"{day_fr} {dt.strftime('%d/%m')}"

        lines = []
        for g in games:
            h = g.get("home_team", {})
            a = g.get("visitor_team", {})
            h_name = h.get("full_name","?")
            a_name = a.get("full_name","?")
            status = g.get("status","TBD")
            lines.append(
                f"{emoji(a_name)} **{a.get('abbreviation','?')}**  🆚  "
                f"{emoji(h_name)} **{h.get('abbreviation','?')}**"
                f"  —  `{status}`"
            )

        embed = discord.Embed(
            title=f"📅  {day_label}  —  {len(games)} match{'s' if len(games)>1 else ''}",
            description="\n".join(lines),
            color=NBA_BLUE,
        )
        embeds.append(embed)

    return embeds

# ─────────────────────────────────────────────────────────────────────────────
#  GAME DAY ANNOUNCEMENT
# ─────────────────────────────────────────────────────────────────────────────

def build_game_announcement(game: dict) -> discord.Embed:
    h = game.get("home_team", {})
    a = game.get("visitor_team", {})
    h_name = h.get("full_name","?")
    a_name = a.get("full_name","?")
    h_abbr = h.get("abbreviation","?")
    a_abbr = a.get("abbreviation","?")
    status = game.get("status","")

    embed = discord.Embed(
        title="🏀  MATCH DU JOUR",
        description=(
            f"## {emoji(a_name)}  {a_name}\n"
            f"# ⚔️  VS\n"
            f"## {emoji(h_name)}  {h_name}\n\n"
            f"> 🕐 **Heure :** `{status}`\n"
            f"> 🏟️ **Domicile :** {h_name}"
        ),
        color=NBA_RED,
        timestamp=datetime.utcnow(),
    )
    embed.set_thumbnail(url=logo(h_abbr))
    embed.set_image(url=logo(a_abbr))
    embed.set_footer(text="NBA Bot Premium • Game Day")
    return embed

# ─────────────────────────────────────────────────────────────────────────────
#  LIVE SCORE
# ─────────────────────────────────────────────────────────────────────────────

def build_live_score(game: dict) -> discord.Embed:
    h = game.get("home_team", {})
    a = game.get("visitor_team", {})
    h_name = h.get("full_name","?")
    a_name = a.get("full_name","?")
    h_score = game.get("home_team_score",0) or 0
    a_score = game.get("visitor_team_score",0) or 0
    period  = game.get("period","?")
    time    = game.get("time","")
    status  = game.get("status","")

    is_live  = status and status != "Final" and ":" not in str(status)
    is_final = status == "Final"

    clr = 0x00FF88 if is_live else (NBA_GOLD if is_final else NBA_BLUE)
    phase = f"🔴 LIVE Q{period} {time}" if is_live else ("🏁 FINAL" if is_final else f"🕐 {status}")

    leading = h_name if h_score >= a_score else a_name

    embed = discord.Embed(title=phase, color=clr, timestamp=datetime.utcnow())
    embed.set_thumbnail(url=logo(h.get("abbreviation","")))
    embed.set_footer(text="NBA Bot Premium • Live")

    embed.description = (
        f"{'🏆 ' if is_final and a_score>h_score else ''}"
        f"{emoji(a_name)}  **{a_name}**\n"
        f"# {a_score}\n\n"
        f"{'🏆 ' if is_final and h_score>a_score else ''}"
        f"{emoji(h_name)}  **{h_name}**\n"
        f"# {h_score}"
    )
    return embed

# ─────────────────────────────────────────────────────────────────────────────
#  BOXSCORE  (feuille de match façon tableau)
# ─────────────────────────────────────────────────────────────────────────────

def build_boxscore(game: dict, stats: list) -> list[discord.Embed]:
    h = game.get("home_team", {})
    a = game.get("visitor_team", {})
    h_name = h.get("full_name","?")
    a_name = a.get("full_name","?")
    h_abbr = h.get("abbreviation","?")
    a_abbr = a.get("abbreviation","?")
    h_score = game.get("home_team_score",0) or 0
    a_score = game.get("visitor_team_score",0) or 0

    winner = h_name if h_score > a_score else a_name
    loser  = a_name if h_score > a_score else h_name
    w_s    = max(h_score, a_score)
    l_s    = min(h_score, a_score)

    # ── Header ──
    header = discord.Embed(
        title=f"📊  FEUILLE DE MATCH  —  {a_abbr} @ {h_abbr}",
        description=(
            f"## {emoji(winner)}  {winner}  gagne\n"
            f"# {emoji(a_name)} {a_score}   —   {h_score} {emoji(h_name)}\n"
            f"*Défaite de {emoji(loser)} {loser} — écart : +{w_s-l_s} pts*"
        ),
        color=color(winner),
        timestamp=datetime.utcnow(),
    )
    header.set_thumbnail(url=logo(h_abbr))
    header.set_footer(text="NBA Bot Premium • Boxscore Final")
    embeds = [header]

    # ── Per-team stats ──
    for team_name, team_abbr in [(a_name, a_abbr), (h_name, h_abbr)]:
        t_stats = [s for s in stats if (s.get("team") or {}).get("full_name") == team_name]
        t_stats.sort(key=lambda x: x.get("pts",0) or 0, reverse=True)
        if not t_stats:
            continue

        # Build table
        rows = ["```"]
        rows.append(f"{'JOUEUR':<22} {'PTS':>4} {'REB':>4} {'PD':>4} {'INT':>4} {'CT':>4} {'TM':>5}")
        rows.append("─" * 48)
        for s in t_stats[:10]:
            p    = s.get("player", {})
            fn   = (p.get("first_name","?") or "?")[0]
            ln   = p.get("last_name","?") or "?"
            name = f"{fn}. {ln}"[:20]
            pts  = s.get("pts",0)  or 0
            reb  = s.get("reb",0)  or 0
            ast  = s.get("ast",0)  or 0
            stl  = s.get("stl",0)  or 0
            blk  = s.get("blk",0)  or 0
            fgm  = s.get("fgm",0)  or 0
            fga  = s.get("fga",0)  or 0
            tm   = f"{fgm}/{fga}"
            rows.append(f"{name:<22} {pts:>4} {reb:>4} {ast:>4} {stl:>4} {blk:>4} {tm:>5}")
        rows.append("```")
        rows.append("*PTS=Points  REB=Rebonds  PD=Passes  INT=Interceptions  CT=Contres  TM=Tirs*")

        e = discord.Embed(
            title=f"{emoji(team_name)}  {team_name}",
            description="\n".join(rows),
            color=color(team_name),
        )
        e.set_thumbnail(url=logo(team_abbr))
        embeds.append(e)

    return embeds

# ─────────────────────────────────────────────────────────────────────────────
#  STANDINGS
# ─────────────────────────────────────────────────────────────────────────────

def build_standings(standings: list, conference: str) -> discord.Embed:
    is_w   = conference == "West"
    label  = "🌅  WESTERN CONFERENCE" if is_w else "🌆  EASTERN CONFERENCE"
    clr    = 0xC8102E if is_w else 0x1D428A

    teams = sorted(
        [s for s in standings if (s.get("conference") or "").lower() == conference.lower()],
        key=lambda x: x.get("conference_rank", 99),
    )

    embed = discord.Embed(title=f"🏆  NBA STANDINGS — {label}", color=clr, timestamp=datetime.utcnow())
    embed.set_thumbnail(url="https://cdn.nba.com/logos/leagues/logo-nba.svg")
    embed.set_footer(text="NBA Bot Premium • Classement mis à jour en temps réel")

    left_lines  = []
    right_lines = []

    for i, s in enumerate(teams):
        t       = s.get("team") or {}
        abbr    = t.get("abbreviation","???")
        name    = t.get("full_name","?")
        em      = emoji(name)
        w       = s.get("wins",0)
        l       = s.get("losses",0)
        pct     = f"{float(s.get('win_pct',0)):.3f}"
        gb      = s.get("games_back") or "-"
        st_type = s.get("streak_type","")
        st_val  = s.get("streak","")
        streak  = f"{'🔥' if st_type=='W' else '❄️'}{st_val}" if st_val else ""

        rank_icon = ["🥇","🥈","🥉"][i] if i < 3 else ("✦" if i < 6 else ("◈" if i < 10 else "✖"))
        line = f"{rank_icon} **#{i+1}** {em} `{abbr}` **{w}W-{l}L** {streak}"

        if i < 8:
            left_lines.append(line)
        else:
            right_lines.append(line)

    embed.add_field(name="─── Top 8 ───", value="\n".join(left_lines) or "─", inline=True)
    embed.add_field(name="─── Suite ───",  value="\n".join(right_lines) or "─", inline=True)
    embed.add_field(
        name="Légende",
        value="🥇🥈🥉 Top 3  •  ✦ Playoff direct  •  ◈ Play-In  •  ✖ Éliminé\n🔥 Win streak  •  ❄️ Lose streak",
        inline=False,
    )
    return embed

# ─────────────────────────────────────────────────────────────────────────────
#  NEWS EMBED
# ─────────────────────────────────────────────────────────────────────────────

def build_news_embed(title: str, summary: str, source: str,
                     image_url: str|None, category: str, published: str="") -> discord.Embed:
    from utils.news_feed import CAT_EMOJI, CAT_LABEL, CAT_COLOR

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

    footer = f"Source : {source}"
    if published:
        footer += f"  •  {published[:10]}"
    embed.set_footer(text=footer)
    return embed
