import os
import anthropic

_client = None

def _c():
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_KEY","")
        if key:
            _client = anthropic.Anthropic(api_key=key)
    return _client

PROMPTS = {
    "injury":  "Tu es journaliste NBA. Résume cette blessure/retour en 3 phrases percutantes EN FRANÇAIS. Joueur, équipe, blessure, impact sur la saison. Style pro et accrocheur.",
    "trade":   "Tu es journaliste NBA. Résume ce transfert/trade en 3 phrases EN FRANÇAIS. Joueurs, équipes, picks, impact. Style dynamique.",
    "draft":   "Tu es journaliste NBA. Résume cette info Draft en 3 phrases EN FRANÇAIS. Joueurs, picks, équipes, enjeu. Style accrocheur.",
    "exploit": "Tu es journaliste NBA. Décris cet exploit sportif en 3 phrases EN FRANÇAIS. Chiffres clés, contexte du match, importance. Style enthousiaste.",
    "news":    "Tu es journaliste NBA. Résume cette actualité NBA en 3-4 phrases percutantes EN FRANÇAIS. Commence par l'info principale. Style journalistique pro. Pas de bullet points.",
}

async def summarize(title: str, content: str, category: str = "news") -> str:
    if not content or len(content) < 50:
        return content or title

    client = _c()
    if not client:
        # No API key: return clean truncation
        return content[:400] + ("..." if len(content) > 400 else "")

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=PROMPTS.get(category, PROMPTS["news"]),
            messages=[{"role":"user","content":f"Titre: {title}\n\nContenu: {content[:2500]}"}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[Claude] {e}")
        return content[:400] + ("..." if len(content) > 400 else "")