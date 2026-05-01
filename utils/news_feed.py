import aiohttp
import feedparser
import hashlib
import os
import re
import random
from typing import Optional

NEWS_KEY = os.getenv("NEWS_API_KEY", "")

RSS_FEEDS = [
    ("ESPN NBA",          "https://www.espn.com/espn/rss/nba/news"),
    ("HoopsHype",         "https://hoopshype.com/feed/"),
    ("Bleacher Report",   "https://bleacherreport.com/articles/feed?tag_id=9"),
    ("RealGM Wiretap",    "https://basketball.realgm.com/rss/wiretap.xml"),
    ("NBA.com",           "https://www.nba.com/news/rss.xml"),
    ("BeBasket 🇫🇷",      "https://www.bebasket.fr/feed/"),
    ("BasketSession 🇫🇷", "https://www.basketsession.com/feed/"),
    ("L'Équipe 🇫🇷",      "https://www.lequipe.fr/rss/actu-article_Basket.xml"),
]

_seen: set[str] = set()


def _uid(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _get_image(entry) -> Optional[str]:
    for attr in ("media_thumbnail", "media_content"):
        val = getattr(entry, attr, None)
        if val:
            u = val[0].get("url", "")
            if u and u.startswith("http"):
                return u
    if getattr(entry, "enclosures", None):
        for enc in entry.enclosures:
            if "image" in enc.get("type", ""):
                u = enc.get("href") or enc.get("url", "")
                if u:
                    return u
    # Fallback: parse img src from HTML
    raw = ""
    if getattr(entry, "content", None):
        raw = entry.content[0].get("value", "")
    elif getattr(entry, "summary", None):
        raw = entry.summary
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
    if m and m.group(1).startswith("http"):
        return m.group(1)
    return None


async def fetch_all_articles(max_per_feed: int = 5) -> list[dict]:
    articles = []
    hdrs = {"User-Agent": "NBABot/2.0 (Discord Bot)"}

    async with aiohttp.ClientSession(headers=hdrs) as session:
        for source, url in RSS_FEEDS:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status != 200:
                        continue
                    raw = await resp.text()
                feed  = feedparser.parse(raw)
                count = 0
                for entry in feed.entries:
                    if count >= max_per_feed:
                        break
                    link = entry.get("link", "")
                    if not link:
                        continue
                    uid = _uid(link)
                    if uid in _seen:
                        continue
                    _seen.add(uid)

                    content = ""
                    if getattr(entry, "content", None):
                        content = _strip_html(entry.content[0].get("value", ""))
                    elif getattr(entry, "summary", None):
                        content = _strip_html(entry.summary)

                    articles.append({
                        "source":    source,
                        "title":     entry.get("title", "").strip(),
                        "content":   content,
                        "image_url": _get_image(entry),
                        "published": entry.get("published", ""),
                    })
                    count += 1
            except Exception as e:
                print(f"[RSS] {source}: {e}")

    # NewsAPI
    if NEWS_KEY:
        for q, lang in [("NBA basketball", "en"), ("NBA basket actualité", "fr")]:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(
                        "https://newsapi.org/v2/everything",
                        params={"q": q, "language": lang, "sortBy": "publishedAt",
                                "pageSize": 10, "apiKey": NEWS_KEY},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as r:
                        if r.status != 200:
                            continue
                        data = await r.json()
                for art in data.get("articles", []):
                    link = art.get("url", "")
                    uid  = _uid(link)
                    if uid in _seen:
                        continue
                    _seen.add(uid)
                    articles.append({
                        "source":    art.get("source", {}).get("name", "NewsAPI"),
                        "title":     (art.get("title", "") or "").strip(),
                        "content":   ((art.get("description","") or "") + " " + (art.get("content","") or "")).strip(),
                        "image_url": art.get("urlToImage"),
                        "published": art.get("publishedAt", ""),
                    })
            except Exception as e:
                print(f"[NewsAPI] {e}")

    random.shuffle(articles)
    return articles


def detect_category(title: str, content: str) -> str:
    """
    Proper category detection — not everything is an injury!
    Uses keyword scoring so the best match wins.
    """
    t = (title + " " + content).lower()

    scores = {
        "injury":  0,
        "trade":   0,
        "draft":   0,
        "exploit": 0,
        "rumor":   0,
        "news":    0,
    }

    # Injury keywords
    for w in ["injur","bless","out indefinitely","day-to-day","questionable","doubtful",
              "knee","ankle","achilles","hamstring","wrist","shoulder","return","retour","absent","miss"]:
        if w in t:
            scores["injury"] += 2

    # Trade keywords
    for w in ["trade","transfert","sign","signing","waive","release","free agent","free-agent",
              "deal","acquire","swap","buyout","contract","extension","option"]:
        if w in t:
            scores["trade"] += 2

    # Draft keywords
    for w in ["draft","pick","prospect","lottery","combine","mock draft","pre-draft"]:
        if w in t:
            scores["draft"] += 2

    # Exploit keywords
    for w in ["career high","career-high","record","triple double","triple-double","quadruple",
              "40 point","50 point","60 point","buzzer","game-winner","exploit","historic"]:
        if w in t:
            scores["exploit"] += 2

    # Rumor keywords
    for w in ["rumor","rumour","report","source","according to","per shams","per woj",
              "expected to","likely to","interest in","targeting"]:
        if w in t:
            scores["rumor"] += 1

    # Pick best
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "news"