import os
import anthropic

_client: anthropic.Anthropic | None = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_KEY",""))
    return _client

SYSTEM_PROMPTS = {
    "injury": (
        "Tu es un journaliste NBA expert. Résume cette info de blessure/retour en 3 phrases percutantes en français. "
        "Mentionne : le joueur, l'équipe, la blessure/situation, et l'impact sur l'équipe. "
        "Style accrocheur, comme un journaliste sportif professionnel. Pas de bullet points."
    ),
    "trade": (
        "Tu es un journaliste NBA expert. Résume ce transfert/trade en 3 phrases en français. "
        "Mentionne : les joueurs échangés, les équipes, les picks impliqués si précisé, et l'impact. "
        "Style dynamique et pro. Pas de bullet points."
    ),
    "draft": (
        "Tu es un journaliste NBA expert. Résume cette info de Draft en 3 phrases en français. "
        "Mentionne : les joueurs/picks, les équipes, et l'enjeu. Style accrocheur. Pas de bullet points."
    ),
    "exploit": (
        "Tu es un journaliste NBA expert. Décris cet exploit sportif en 3 phrases en français. "
        "Mets en valeur les performances, les chiffres clés, et le contexte du match. "
        "Style enthousiaste et pro. Pas de bullet points."
    ),
    "news": (
        "Tu es un journaliste NBA expert. Résume cette actualité NBA en 3-4 phrases percutantes en français. "
        "Commence directement par l'information principale. Style journalistique pro, dynamique. "
        "Pas de bullet points, texte fluide."
    ),
}

async def summarize(title: str, content: str, category: str = "news") -> str:
    if not content or len(content) < 60:
        return content or title

    system = SYSTEM_PROMPTS.get(category, SYSTEM_PROMPTS["news"])
    try:
        client = _get_client()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",   # fast + cheap
            max_tokens=350,
            system=system,
            messages=[{"role":"user","content":f"Titre: {title}\n\nContenu: {content[:2500]}"}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[Claude] summarize error: {e}")
        return content[:500] + ("..." if len(content) > 500 else "")
