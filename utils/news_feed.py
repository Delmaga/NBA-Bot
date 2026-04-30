import aiohttp
import feedparser
import hashlib
import os
import re
from typing import Optional

NEWS_KEY = os.getenv("NEWS_API_KEY", "")

RSS_FEEDS = [
    ("ESPN NBA",         "https://www.espn.com/espn/rss/nba/news"),
    ("HoopsHype",        "https://hoopshype.com/feed/"),
    ("Bleacher Report",  "https://bleacherreport.com/articles/feed?tag_id=9"),
    ("BeBasket 🇫🇷",     "https://www.bebasket.fr/feed/"),
    ("BasketSession 🇫🇷","https://www.basketsession.com/feed/"),
    ("L'Équipe 🇫🇷",     "https://www.lequipe.fr/rss/actu-article_Basket.xml"),
    ("RealGM",           "https://basketball.realgm.com/rss/wiretap.xml"),
]

_seen: set[str] = set()

def _uid(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def _strip(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()

def _extract_image(entry) -> Optional[str]:
    for attr in ("media_thumbnail", "media_content"):
        val = getattr(entry, attr, None)
        if val:
            return val[0].get("url")
    if getattr(entry, "enclosures", None):
        for e in entry.enclosures:
            if "image" in e.get("type",""):
                return e.get("href") or e.get("url")
    # Try content HTML for img src
    content = ""
    if getattr(entry, "content", None):
        content = entry.content[0].get("value","")
    elif getattr(entry, "summary", None):
        content = entry.summary
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
    if m:
        return m.group(1)
    return None

async def fetch_rss(max_per_feed: int = 5) -> list[dict]:
    articles = []
    async with aiohttp.ClientSession() as session:
        for source, url in RSS_FEEDS:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8),
                                       headers={"User-Agent": "NBABot/1.0"}) as resp:
                    if resp.status != 200:
                        continue
                    raw = await resp.text()
                feed = feedparser.parse(raw)
                count = 0
                for entry in feed.entries:
                    if count >= max_per_feed:
                        break
                    link = entry.get("link","")
                    if not link:
                        continue
                    uid = _uid(link)
                    if uid in _seen:
                        continue
                    _seen.add(uid)

                    content = ""
                    if getattr(entry,"content",None):
                        content = _strip(entry.content[0].get("value",""))
                    elif getattr(entry,"summary",None):
                        content = _strip(entry.summary)

                    articles.append({
                        "source":    source,
                        "title":     entry.get("title",""),
                        "content":   content,
                        "image_url": _extract_image(entry),
                        "published": entry.get("published",""),
                    })
                    count += 1
            except Exception as e:
                print(f"[RSS] {source}: {e}")
    return articles

async def fetch_newsapi(query: str = "NBA", lang: str = "en") -> list[dict]:
    if not NEWS_KEY:
        return []
    url = "https://newsapi.org/v2/everything"
    params = {"q": query, "language": lang, "sortBy": "publishedAt",
               "pageSize": 15, "apiKey": NEWS_KEY}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params,
                             timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return []
                data = await r.json()
        out = []
        for art in data.get("articles", []):
            link = art.get("url","")
            uid  = _uid(link)
            if uid in _seen:
                continue
            _seen.add(uid)
            content = (art.get("description","") or "") + " " + (art.get("content","") or "")
            out.append({
                "source":    art.get("source",{}).get("name","NewsAPI"),
                "title":     art.get("title",""),
                "content":   content.strip(),
                "image_url": art.get("urlToImage"),
                "published": art.get("publishedAt",""),
            })
        return out
    except Exception as e:
        print(f"[NewsAPI] {e}")
        return []

def detect_category(title: str, content: str) -> str:
    t = (title + " " + content).lower()
    if any(w in t for w in ["injur","bless","out ","absent","miss","return","retour","knee","ankle","achilles"]):
        return "injury"
    if any(w in t for w in ["trade","transfert","sign","signe","waive","release","free agent","deal","acquire"]):
        return "trade"
    if any(w in t for w in ["draft","pick","prospect","lottery","combine"]):
        return "draft"
    if any(w in t for w in ["record","exploit","career high","triple double","quadruple"]):
        return "exploit"
    return "news"

CAT_EMOJI = {"injury":"🏥","trade":"🔄","draft":"📋","exploit":"🌟","news":"📰"}
CAT_LABEL = {"injury":"BLESSURE / RETOUR","trade":"TRANSFERT / TRADE",
             "draft":"DRAFT","exploit":"EXPLOIT","news":"ACTUALITÉ NBA"}
CAT_COLOR = {"injury":0xFF6B35,"trade":0xC9A227,"draft":0x00B4D8,
             "exploit":0xFFD700,"news":0xE8174B}
