import os
import anthropic

_client = None

def _get_client():
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_KEY", "")
        if key:
            _client = anthropic.Anthropic(api_key=key)
    return _client

PROMPTS = {
    "injury":  "Tu es journaliste NBA. Résume cette info de blessure/retour de joueur en 3 phrases EN FRANÇAIS. Nomme le joueur, son équipe, la nature de la blessure/retour, et l'impact sur la saison. Style journalistique pro.",
    "trade":   "Tu es journaliste NBA. Résume ce transfert/trade en 3 phrases EN FRANÇAIS. Joueurs, équipes, conditions, impact. Style dynamique et précis.",
    "draft":   "Tu es journaliste NBA. Résume cette info de Draft NBA en 3 phrases EN FRANÇAIS. Joueurs, picks, équipes, enjeux. Style accrocheur.",
    "exploit": "Tu es journaliste NBA. Décris cet exploit en 3 phrases EN FRANÇAIS. Performance, chiffres clés, contexte. Style enthousiaste.",
    "rumor":   "Tu es journaliste NBA. Résume cette rumeur/info de source en 3 phrases EN FRANÇAIS. Qui, quoi, source, fiabilité. Style neutre et factuel.",
    "news":    "Tu es journaliste NBA. Résume cette actualité NBA en 3-4 phrases EN FRANÇAIS. Commence par l'info principale. Style journalistique pro, direct. Pas de bullet points.",
}

async def summarize(title: str, content: str, category: str = "news") -> str:
    if not content or len(content) < 50:
        return content or title

    client = _get_client()
    if not client:
        # Fallback sans API key
        return content[:450] + ("..." if len(content) > 450 else "")

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=PROMPTS.get(category, PROMPTS["news"]),
            messages=[{"role": "user", "content": f"Titre: {title}\n\nContenu: {content[:2500]}"}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[Claude] {e}")
        return content[:450] + ("..." if len(content) > 450 else "")