from __future__ import annotations

import re

from mtg_deck_rec.api.client import client
from mtg_deck_rec.models import EDHRECCard

EDHREC_JSON_BASE = "https://json.edhrec.com/pages/commanders"


def commander_name_to_slug(name: str) -> str:
    """Convert 'Ezuri, Claw of Progress' to 'ezuri-claw-of-progress'."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def fetch_recommendations(commander_name: str) -> list[EDHRECCard]:
    """Fetch EDHREC card recommendations for a commander."""
    slug = commander_name_to_slug(commander_name)
    url = f"{EDHREC_JSON_BASE}/{slug}.json"
    data = client.get_json(url)

    container = data.get("container", {})
    json_dict = container.get("json_dict", {})
    cardlists = json_dict.get("cardlists", [])

    cards: list[EDHRECCard] = []
    seen: set[str] = set()

    for cardlist in cardlists:
        category = cardlist.get("header", "Unknown")
        for cv in cardlist.get("cardviews", []):
            name = cv.get("name", "")
            if not name:
                continue
            # Deduplicate — a card can appear in multiple categories.
            # Keep the first occurrence (higher-priority category).
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)

            cards.append(
                EDHRECCard(
                    name=name,
                    synergy=cv.get("synergy", 0.0),
                    num_decks=cv.get("num_decks", 0),
                    potential_decks=cv.get("potential_decks", 0),
                    category=category,
                )
            )

    return cards
