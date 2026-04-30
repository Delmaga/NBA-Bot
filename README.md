# 🏀 NBA Premium Bot

Bot Discord premium pour suivre la NBA : scores live, feuilles de match, classements auto-mis à jour, et actualités résumées par IA.

---

## 🚀 APIs nécessaires (toutes gratuites ou quasi)

| API | Usage | Lien | Prix |
|-----|-------|------|------|
| **Discord** | Bot token | [discord.com/developers](https://discord.com/developers/applications) | Gratuit |
| **BallDontLie** | Scores, matchs, stats, classements | [balldontlie.io](https://www.balldontlie.io) | Gratuit |
| **Anthropic Claude** | Résumés IA des articles | [console.anthropic.com](https://console.anthropic.com) | ~1-2€/mois |
| **NewsAPI** | Articles NBA du monde entier | [newsapi.org](https://newsapi.org) | Gratuit (100 req/j) |

---

## ⚙️ Installation

### 1. Clone & install
```bash
cd nba-bot
pip install -r requirements.txt
```

### 2. Configuration
```bash
cp .env.example .env
# Remplis les valeurs dans .env
```

### 3. Discord Developer Portal
1. Va sur https://discord.com/developers/applications
2. Sélectionne ton bot → **Bot**
3. Active les **3 Privileged Gateway Intents** :
   - ✅ Presence Intent
   - ✅ Server Members Intent  
   - ✅ Message Content Intent
4. **Save Changes**

### 4. Créer les 3 salons Discord
- `#nba-match` → scores, feuilles de match, programme
- `#nba-classement` → standings auto-mis à jour
- `#nba-news` → actualités NBA toutes les 15 min

Clic droit sur chaque salon → **Copier l'identifiant**  
(Active d'abord : Paramètres → Avancé → Mode développeur)

### 5. Lancer
```bash
python main.py
```

---

## 📋 Commandes slash

| Commande | Description |
|----------|-------------|
| `/nba_match` | Scores du jour |
| `/nba_week` | Programme des 7 prochains jours |
| `/nba_classement` | Standings West & East |
| `/nba_news` | 5 dernières actualités NBA |

---

## 🔄 Automatismes

| Quand | Quoi | Salon |
|-------|------|-------|
| Lundi 8h | Programme de la semaine | `#nba-match` |
| Avant chaque match | Annonce du match | `#nba-match` |
| Toutes les 3 min | Score live (si match en cours) | `#nba-match` |
| Fin de match | Feuille de match complète | `#nba-match` |
| Après chaque match | Classement de la conférence mis à jour | `#nba-classement` |
| Toutes les 30 min | Mise à jour silencieuse des classements | `#nba-classement` |
| Toutes les 15 min | Nouvelles actualités NBA (résumées par IA) | `#nba-news` |

---

## 🚂 Déploiement Railway

```bash
git init && git add . && git commit -m "NBA Bot"
# Push sur GitHub → railway.app → Deploy from GitHub
# Ajoute les variables .env dans Railway → Variables
```

---

## 📁 Structure
```
nba-bot/
├── main.py
├── Procfile
├── requirements.txt
├── .env.example
├── cogs/
│   ├── match.py       → matchs, live, boxscore, programme hebdo
│   ├── classement.py  → standings auto-éditables
│   └── news.py        → actualités RSS + NewsAPI + résumés IA
└── utils/
    ├── nba_api.py     → BallDontLie API wrapper
    ├── news_feed.py   → RSS + NewsAPI fetcher
    ├── ai_summary.py  → Claude résumés
    └── formatters.py  → tous les embeds Discord
```
