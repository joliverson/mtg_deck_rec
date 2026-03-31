from __future__ import annotations

from mtg_deck_rec.models import ComparisonEntry, ComparisonResult


SEPARATOR = "─"


def _format_synergy(entry: ComparisonEntry) -> str:
    if entry.edhrec is None:
        return "  N/A"
    return f"{entry.edhrec.synergy:+.2f}"


def _format_inclusion(entry: ComparisonEntry) -> str:
    if entry.edhrec is None:
        return "  N/A"
    return f"{entry.edhrec.inclusion_rate * 100:5.1f}%"


def _format_category(entry: ComparisonEntry) -> str:
    if entry.edhrec is None:
        return "Not in EDHREC"
    return entry.edhrec.category


def _card_name(entry: ComparisonEntry) -> str:
    if entry.card:
        return entry.card.name
    if entry.edhrec:
        return entry.edhrec.name
    return "?"


def _print_table(entries: list[ComparisonEntry], top_n: int) -> None:
    if not entries:
        print("  (none)")
        return

    headers = ("Card Name", "Synergy", "Inclusion", "Category")
    col_widths = (34, 8, 10, 22)

    header_line = "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    sep_line = "  ".join(SEPARATOR * w for w in col_widths)

    print(f"  {header_line}")
    print(f"  {sep_line}")

    for entry in entries[:top_n]:
        name = _card_name(entry)
        row = (
            name[:col_widths[0]].ljust(col_widths[0]),
            _format_synergy(entry).ljust(col_widths[1]),
            _format_inclusion(entry).ljust(col_widths[2]),
            _format_category(entry)[:col_widths[3]].ljust(col_widths[3]),
        )
        print(f"  {'  '.join(row)}")


def print_comparison(result: ComparisonResult, top_n: int = 25) -> None:
    """Print the full comparison report to stdout."""
    print()
    print(f"=== DECK: {result.deck_name} (Commander: {result.commander_name}) ===")
    print()

    # Validated
    print(f"✓ VALIDATED CHOICES — {len(result.validated)} cards EDHREC agrees with:")
    _print_table(result.validated, top_n)
    print()

    # Recommended adds
    print(f"+ RECOMMENDED ADDITIONS — {len(result.recommended_adds)} cards to consider:")
    _print_table(result.recommended_adds, top_n)
    print()

    # Potential cuts
    print(f"✗ POTENTIAL CUTS — {len(result.potential_cuts)} cards with low/no EDHREC presence:")
    _print_table(result.potential_cuts, top_n)
    print()
