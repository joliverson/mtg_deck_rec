from __future__ import annotations

import re

from mtg_deck_rec.api.client import APIError, client
from mtg_deck_rec.models import Card, Deck

MOXFIELD_API_BASE = "https://api2.moxfield.com/v3/decks/all"


def parse_deck_id(url_or_id: str) -> str:
    """Extract deck ID from a Moxfield URL or return raw ID."""
    match = re.search(r"moxfield\.com/decks/([A-Za-z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)
    # Assume it's a raw ID already
    return url_or_id.strip()


def _parse_card(entry: dict) -> Card:
    card_data = entry.get("card", {})
    return Card(
        name=card_data.get("name", "Unknown"),
        quantity=entry.get("quantity", 1),
        type_line=card_data.get("type_line", ""),
        mana_cost=card_data.get("mana_cost", ""),
        cmc=card_data.get("cmc", 0.0),
        scryfall_id=card_data.get("scryfall_id"),
    )


def fetch_deck(deck_id: str) -> Deck:
    """Fetch and parse a deck from the Moxfield API."""
    url = f"{MOXFIELD_API_BASE}/{deck_id}"
    data = client.get_json(url)

    boards = data.get("boards", {})

    # Parse commander(s) — nested under boards.commanders.cards
    commanders_board = boards.get("commanders", {})
    commander_cards = commanders_board.get("cards", {})
    if not commander_cards:
        raise APIError("No commander found in deck data")
    commander_entry = next(iter(commander_cards.values()))
    commander = _parse_card(commander_entry)

    # Parse mainboard — nested under boards.mainboard.cards
    mainboard_board = boards.get("mainboard", {})
    mainboard_cards = mainboard_board.get("cards", {})
    mainboard = [_parse_card(entry) for entry in mainboard_cards.values()]

    deck_name = data.get("name", "Unknown Deck")
    public_url = data.get("publicUrl", "")
    if public_url and not public_url.startswith("http"):
        public_url = f"https://moxfield.com/decks/{deck_id}"

    return Deck(
        name=deck_name,
        url=public_url,
        commander=commander,
        mainboard=mainboard,
        format=data.get("format", "commander"),
    )
