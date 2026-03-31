from __future__ import annotations

from mtg_deck_rec.models import (
    ComparisonEntry,
    ComparisonResult,
    Deck,
    EDHRECCard,
    normalize_card_name,
)


def compare(
    deck: Deck,
    edhrec_cards: list[EDHRECCard],
    add_threshold: float = 0.20,
    cut_threshold: float = 0.10,
) -> ComparisonResult:
    """Compare a deck's mainboard against EDHREC recommendations.

    Args:
        deck: The user's deck from Moxfield.
        edhrec_cards: EDHREC recommendations for the commander.
        add_threshold: Minimum inclusion rate to recommend adding a card.
        cut_threshold: Below this inclusion rate, flag as a potential cut.
    """
    # Build lookup of EDHREC cards by normalized name
    edhrec_by_name: dict[str, EDHRECCard] = {
        c.normalized_name: c for c in edhrec_cards
    }

    # Sets for quick membership testing
    deck_names = deck.card_names
    commander_normalized = normalize_card_name(deck.commander.name)

    validated: list[ComparisonEntry] = []
    potential_cuts: list[ComparisonEntry] = []

    for card in deck.mainboard:
        norm = card.normalized_name
        # Skip the commander itself
        if norm == commander_normalized:
            continue

        edhrec_match = edhrec_by_name.get(norm)

        if edhrec_match and edhrec_match.inclusion_rate >= cut_threshold:
            # Card is in EDHREC with reasonable inclusion — validated
            validated.append(ComparisonEntry(card=card, edhrec=edhrec_match))
        else:
            # Card either not in EDHREC, or has very low inclusion
            potential_cuts.append(ComparisonEntry(card=card, edhrec=edhrec_match))

    # Recommended adds: EDHREC cards NOT in the deck with good inclusion
    recommended_adds: list[ComparisonEntry] = []
    for ec in edhrec_cards:
        if ec.normalized_name in deck_names:
            continue
        if ec.normalized_name == commander_normalized:
            continue
        if ec.inclusion_rate >= add_threshold:
            recommended_adds.append(ComparisonEntry(card=None, edhrec=ec))

    # Sort
    validated.sort(key=lambda e: (e.edhrec.synergy if e.edhrec else 0), reverse=True)
    recommended_adds.sort(
        key=lambda e: (e.edhrec.synergy if e.edhrec else 0, e.edhrec.inclusion_rate if e.edhrec else 0),
        reverse=True,
    )
    potential_cuts.sort(
        key=lambda e: (e.edhrec.inclusion_rate if e.edhrec else -1),
    )

    return ComparisonResult(
        deck_name=deck.name,
        commander_name=deck.commander.name,
        validated=validated,
        recommended_adds=recommended_adds,
        potential_cuts=potential_cuts,
    )
