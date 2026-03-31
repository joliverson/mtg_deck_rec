from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Card:
    name: str
    quantity: int = 1
    type_line: str = ""
    mana_cost: str = ""
    cmc: float = 0.0
    scryfall_id: str | None = None

    @property
    def normalized_name(self) -> str:
        return normalize_card_name(self.name)


@dataclass
class Deck:
    name: str
    url: str
    commander: Card
    mainboard: list[Card] = field(default_factory=list)
    format: str = "commander"

    @property
    def card_names(self) -> set[str]:
        return {c.normalized_name for c in self.mainboard}


@dataclass
class EDHRECCard:
    name: str
    synergy: float = 0.0
    num_decks: int = 0
    potential_decks: int = 0
    category: str = ""

    @property
    def normalized_name(self) -> str:
        return normalize_card_name(self.name)

    @property
    def inclusion_rate(self) -> float:
        if self.potential_decks == 0:
            return 0.0
        return self.num_decks / self.potential_decks


@dataclass
class ComparisonEntry:
    card: Card | None
    edhrec: EDHRECCard | None


@dataclass
class ComparisonResult:
    deck_name: str
    commander_name: str
    validated: list[ComparisonEntry] = field(default_factory=list)
    recommended_adds: list[ComparisonEntry] = field(default_factory=list)
    potential_cuts: list[ComparisonEntry] = field(default_factory=list)


def normalize_card_name(name: str) -> str:
    # Handle double-faced cards: take only the front face
    name = name.split("//")[0]
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()
