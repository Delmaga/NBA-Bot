import discord
from datetime import datetime
from utils.nba_api import team_logo, team_color, team_name

NBA_RED  = 0xE8174B
NBA_BLUE = 0x17408B
NBA_GOLD = 0xC9A227

DAYS_FR = {
    "Monday":"Lundi","Tuesday":"Mardi","Wednesday":"Mercredi",
    "Thursday":"Jeudi","Friday":"Vendredi","Saturday":"Samedi","Sunday":"Dimanche"
}

# ─────────────────────────────────────────────────────────────────────────────
#  MATCH ANNOUNCEMENT  (1h avant)
# ─────────────────────────────────────────────────────────────────────────────

def build_game_announcement(game: dict) -> discord.Embed:
    h = game["home_abbr"]
    a = game["away_abbr"]
    series = game.get("series","")

    embed = discord.Embed(
        color=NBA_RED,
        timestamp=datetime.utcnow(),
    )
    embed.set_author(
        name="🏀  MATCH DANS 1 HEURE",
        icon_url="https://cdn.nba.com/logos/leagues/logo-nba.svg"
    )

    embed.add_field(
        name=game["away_name"],
        value=f"`{game.get('away_record','')}`",
        inline=True
    )
    embed.add_field(name="VS", value=f"`{game['status_text']}`", inline=True)
    embed.add_field(
        name=game["home_name"],
        value=f"`{game.get('home_record','')}`",
        inline=True
    )

    if series:
        embed.add_field(name="🏆 Playoffs", value=f"**{series}**", inline=False)
    if game.get("arena"):
        embed.add_field(name="🏟️ Arena", value=game["arena"], inline=False)

    # Away logo as thumbnail, home logo as image
    embed.set_thumbnail(url=team_logo(a))
    embed.set_image(url=team_logo(h))
    embed.set_footer(text="NBA Bot Premium • Game Day")
    return embed

# ─────────────────────────────────────────────────────────────────────────────
#  FINAL SCORE
# ─────────────────────────────────────────────────────────────────────────────

def build_final_score(game: dict) -> discord.Embed:
    h   = game["home_abbr"]
    a   = game["away_abbr"]
    h_s = game["home_score"]
    a_s = game["away_score"]

    winner_abbr = h if h_s > a_s else a
    loser_abbr  = a if h_s > a_s else h
    diff        = abs(h_s - a_s)
    series      = game.get("series","")

    embed = discord.Embed(
        title="🏁  FIN DE MATCH",
        color=team_color(winner_abbr),
        timestamp=datetime.utcnow(),
    )
    embed.set_author(
        name="NBA Bot Premium • Résultat Final",
        icon_url="https://cdn.nba.com/logos/leagues/logo-nba.svg"
    )

    embed.add_field(
        name=f"{'🏆 ' if a_s > h_s else ''}{game['away_name']}",
        value=f"# {a_s}",
        inline=True
    )
    embed.add_field(name="—", value="**FINAL**", inline=True)
    embed.add_field(
        name=f"{'🏆 ' if h_s > a_s else ''}{game['home_name']}",
        value=f"# {h_s}",
        inline=True
    )

    embed.add_field(
        name="📊 Résumé",
        value=f"Victoire de **{team_name(winner_abbr)}** par +{diff} points",
        inline=False
    )
    if series:
        embed.add_field(name="🏆 Série", value=f"**{series}**", inline=False)

    embed.set_thumbnail(url=team_logo(winner_abbr))
    embed.set_footer(text="NBA Bot Premium • Score Final")
    return embed

# ─────────────────────────────────────────────────────────────────────────────
#  BOXSCORE (feuille de match)
# ─────────────────────────────────────────────────────────────────────────────

def build_boxscore(game: dict, bs: Optional[dict]) -> list[discord.Embed]:
    h   = game["home_abbr"]
    a   = game["away_abbr"]
    h_s = game["home_score"]
    a_s = game["away_score"]
    winner_abbr = h if h_s > a_s else a

    embeds = []

    # ── Per-team stat table ──
    for side_key, abbr, name in [("away", a, game["away_name"]), ("home", h, game["home_name"])]:
        players = (bs or {}).get(side_key, [])
        if not players:
            continue

        rows = ["```"]
        rows.append(f"{'JOUEUR':<22} {'MIN':>5} {'PTS':>4} {'REB':>4} {'PD':>3} {'INT':>3} {'CT':>3} {'TM':>5} {'3P':>3}")
        rows.append("─" * 56)
        for p in players[:12]:
            nm = p["name"][:20]
            rows.append(
                f"{nm:<22} {p['min']:>5} {p['pts']:>4} {p['reb']:>4} "
                f"{p['ast']:>3} {p['stl']:>3} {p['blk']:>3} "
                f"{p['fgm']}/{p['fga']:<3} {p['tpm']:>3}"
            )
        rows.append("```")
        rows.append("*MIN · PTS · REB · PD=Passes · INT=Interceptions · CT=Contres · TM=Tirs · 3P=3pts*")

        embed = discord.Embed(
            title=f"{name}",
            description="\n".join(rows),
            color=team_color(abbr),
        )
        embed.set_thumbnail(url=team_logo(abbr))
        embeds.append(embed)

    return embeds

# ─────────────────────────────────────────────────────────────────────────────
#  WEEKLY SCHEDULE
# ─────────────────────────────────────────────────────────────────────────────

def build_weekly_embeds(schedule: dict[str, list]) -> list[discord.Embed]:
    from datetime import datetime as dt

    total  = sum(len(v) for v in schedule.values())
    header = discord.Embed(
        title="🗓️  NBA — Programme de la Semaine",
        description=(
            f"**{total} match(s) au programme**  •  "
            f"{list(schedule.keys())[0]} → {list(schedule.keys())[-1]}\n"
            f"{'━'*36}"
        ),
        color=NBA_RED,
        timestamp=datetime.utcnow(),
    )
    header.set_thumbnail(url="https://cdn.nba.com/logos/leagues/logo-nba.svg")
    header.set_footer(text="NBA Bot Premium • Programme Hebdomadaire")

    embeds = [header]
    for day_iso, games in schedule.items():
        if not games:
            continue
        d      = dt.strptime(day_iso, "%Y-%m-%d")
        day_fr = DAYS_FR.get(d.strftime("%A"), d.strftime("%A"))

        lines = []
        for g in games:
            h = g["home_abbr"]
            a = g["away_abbr"]
            lines.append(
                f"**{g['away_name']}** `{a}`  vs  **{g['home_name']}** `{h}`"
                f"  —  `{g['status']}`"
            )

        embed = discord.Embed(
            title=f"📅  {day_fr} {d.strftime('%d/%m')}  —  {len(games)} match{'s' if len(games)>1 else ''}",
            description="\n".join(lines),
            color=NBA_BLUE,
        )
        embeds.append(embed)

    return embeds

# ─────────────────────────────────────────────────────────────────────────────
#  STANDINGS
# ─────────────────────────────────────────────────────────────────────────────

def build_standings_embed(teams: list, conference: str, season_type: str) -> discord.Embed:
    is_west = conference == "West"
    conf_label = "WESTERN" if is_west else "EASTERN"
    clr = 0xC8102E if is_west else 0x1D428A

    type_labels = {
        "Regular Season": "🏀 SAISON RÉGULIÈRE",
        "Playoffs":       "🏆 PLAYOFFS",
        "PlayIn":         "🎟️ PLAY-IN TOURNAMENT",
    }
    type_label = type_labels.get(season_type, season_type)

    embed = discord.Embed(
        title=f"{type_label} — {'🌅' if is_west else '🌆'} {conf_label} CONFERENCE",
        color=clr,
        timestamp=datetime.utcnow(),
    )
    embed.set_thumbnail(url="https://cdn.nba.com/logos/leagues/logo-nba.svg")
    embed.set_footer(text="NBA Bot Premium • Mis à jour automatiquement")

    if not teams:
        embed.description = "> Aucune donnée disponible pour ce type de saison."
        return embed

    lines = []
    for i, t in enumerate(teams):
        abbr = t["abbr"]
        w    = t["wins"]
        l    = t["losses"]
        pct  = f"{t['pct']:.3f}"
        gb   = t["gb"]
        l10  = t["l10"]
        sk   = t["streak"]

        # Rank badge
        if i == 0:   badge = "🥇"
        elif i == 1: badge = "🥈"
        elif i == 2: badge = "🥉"
        elif i < 6:  badge = "✦"
        elif i < 10: badge = "◈"
        else:        badge = "✖"

        # Streak
        sk_icon = ""
        if sk:
            n = "".join(filter(str.isdigit, sk))
            sk_icon = f"🔥{n}" if "W" in sk else f"❄️{n}"

        lines.append(
            f"{badge} **#{i+1}** **{t['name']}** `{abbr}`  "
            f"**{w}W-{l}L**  `{pct}`  GB:{gb}  L10:{l10}  {sk_icon}"
        )

        # Separator lines
        if season_type == "Regular Season":
            if i == 5:
                lines.append("─────────── 🎟️ Play-In ↓")
            elif i == 9:
                lines.append("─────────── ✖ Éliminé ↓")

    embed.description = "\n".join(lines)
    embed.add_field(
        name="Légende",
        value=(
            "🥇🥈🥉 Top 3  •  ✦ Playoff direct  •  ◈ Play-In\n"
            "🔥 Win streak  •  ❄️ Lose streak  •  GB=Games Behind  •  L10=10 derniers matchs"
        ),
        inline=False,
    )
    return embed

# ─────────────────────────────────────────────────────────────────────────────
#  NEWS EMBED
# ─────────────────────────────────────────────────────────────────────────────

CAT_EMOJI = {"injury":"🏥","trade":"🔄","draft":"📋","exploit":"🌟","news":"📰","rumor":"💬"}
CAT_LABEL = {
    "injury":"BLESSURE / RETOUR","trade":"TRANSFERT / TRADE",
    "draft":"DRAFT","exploit":"EXPLOIT","news":"ACTUALITÉ NBA","rumor":"RUMEUR"
}
CAT_COLOR = {
    "injury":0xFF6B35,"trade":0xC9A227,"draft":0x00B4D8,
    "exploit":0xFFD700,"news":0xE8174B,"rumor":0x9B59B6
}

def build_news_embed(title: str, summary: str, source: str,
                     image_url, category: str, published: str = "") -> discord.Embed:
    cat_e = CAT_EMOJI.get(category, "📰")
    cat_l = CAT_LABEL.get(category, "ACTUALITÉ NBA")
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
    embed.set_footer(
        text=f"Source : {source}" + (f"  •  {published[:10]}" if published else "")
    )
    return embed

# Type hint fix
from typing import Optional