from __future__ import annotations

import argparse
import json
import sys

from mtg_deck_rec.analysis.comparator import compare
from mtg_deck_rec.api.client import APIError
from mtg_deck_rec.api.edhrec import fetch_recommendations
from mtg_deck_rec.api.moxfield import fetch_deck, parse_deck_id
from mtg_deck_rec.display.terminal import print_comparison


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mtg-deck-rec",
        description="Compare your MTG Commander deck against EDHREC recommendations.",
    )
    parser.add_argument(
        "deck",
        nargs="?",
        default=None,
        help="Moxfield deck URL or deck ID (e.g. https://moxfield.com/decks/abc123 or abc123)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the web UI instead of CLI output",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for the web UI (default: 5000)",
    )
    parser.add_argument(
        "--add-threshold",
        type=float,
        default=0.20,
        help="Minimum EDHREC inclusion rate to recommend adding a card (default: 0.20)",
    )
    parser.add_argument(
        "--cut-threshold",
        type=float,
        default=0.10,
        help="Below this EDHREC inclusion rate, flag card as potential cut (default: 0.10)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Max number of cards to show per section (default: 25)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output raw JSON instead of formatted tables",
    )
    return parser


def _result_to_dict(result) -> dict:
    def entry_to_dict(entry):
        d = {}
        if entry.card:
            d["card"] = entry.card.name
        if entry.edhrec:
            d["edhrec_name"] = entry.edhrec.name
            d["synergy"] = entry.edhrec.synergy
            d["inclusion_rate"] = round(entry.edhrec.inclusion_rate, 4)
            d["category"] = entry.edhrec.category
        return d

    return {
        "deck_name": result.deck_name,
        "commander": result.commander_name,
        "validated": [entry_to_dict(e) for e in result.validated],
        "recommended_adds": [entry_to_dict(e) for e in result.recommended_adds],
        "potential_cuts": [entry_to_dict(e) for e in result.potential_cuts],
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.web:
        from mtg_deck_rec.web.app import create_app

        app = create_app()
        print(f"Starting web UI at http://localhost:{args.port}")
        app.run(host="127.0.0.1", port=args.port, debug=True)
        return 0

    if not args.deck:
        parser.error("deck URL/ID is required (or use --web to launch the web UI)")

    deck_id = parse_deck_id(args.deck)

    try:
        print(f"Fetching deck {deck_id} from Moxfield...")
        deck = fetch_deck(deck_id)
        print(f"  → {deck.name} — Commander: {deck.commander.name}")
        print(f"  → {len(deck.mainboard)} mainboard cards")

        print(f"Fetching EDHREC data for {deck.commander.name}...")
        edhrec_cards = fetch_recommendations(deck.commander.name)
        print(f"  → {len(edhrec_cards)} recommended cards found")

        print("Comparing...")
        result = compare(
            deck,
            edhrec_cards,
            add_threshold=args.add_threshold,
            cut_threshold=args.cut_threshold,
        )

        if args.json_output:
            print(json.dumps(_result_to_dict(result), indent=2))
        else:
            print_comparison(result, top_n=args.top_n)

    except APIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
