"""Build MTG-specific prompts for deck analysis and card recommendations."""

from __future__ import annotations

from mtg_deck_rec.models import ComparisonResult, EDHRECCard


SYSTEM_PROMPT = """\
You are an expert Magic: The Gathering Commander/EDH deck-building advisor. \
You have deep knowledge of card interactions, synergies, mana curves, win \
conditions, and the Commander format meta.

When analyzing a deck, you consider:
- The commander's abilities and how to maximize their value
- Mana curve and ramp balance
- Win conditions and how the deck closes out games
- Card synergies and combo potential
- Interaction and removal suite
- Card draw and card advantage engines
- Board presence and threat density

Format your response in clean Markdown with headers and bullet points. \
Be specific about card names and explain WHY each swap matters in terms \
of how the deck plays. Focus on the most impactful changes first. \
Keep recommendations practical — suggest specific "cut X for Y" swaps \
when possible."""


VISION_SYSTEM_PROMPT = """\
You are a Magic: The Gathering card identification expert. \
Your task is to identify every MTG card visible in the image. \
Return ONLY a JSON array of card names, one per card visible. \
Use the exact official card name as printed. \
If a card is partially obscured but identifiable, include it. \
If you cannot identify a card at all, skip it. \
Return valid JSON only — no explanation, no markdown fences."""


EVALUATE_SYSTEM_PROMPT = """\
You are an expert Magic: The Gathering Commander/EDH deck-building advisor \
providing statistically-grounded card evaluations.

When evaluating candidate cards for a deck, you use a multi-factor scoring system:

1. **EDHREC Synergy Score** (weight: 30%) — How synergistic is this card with \
the commander, based on EDHREC data? Range -1.0 to +1.0.
2. **EDHREC Inclusion Rate** (weight: 25%) — What percentage of decks for this \
commander run this card? Higher = more proven.
3. **Strategic Fit** (weight: 25%) — How well does this card support the \
commander's primary game plan and win conditions?
4. **Mana Efficiency** (weight: 20%) — Is the mana cost appropriate for the \
effect? Does it fit the deck's curve?

Score each card 1-10 on each factor, then compute a weighted composite score. \
Present results in a clear table and explain the reasoning.

Format your response in clean Markdown."""


def build_analysis_prompt(result: ComparisonResult) -> str:
    """Build a user prompt from comparison data for LLM analysis."""

    # Top validated cards (abbreviated)
    validated_lines = []
    for e in result.validated[:15]:
        if e.edhrec:
            validated_lines.append(
                f"  - {e.edhrec.name} (synergy: {e.edhrec.synergy:+.2f}, "
                f"inclusion: {e.edhrec.inclusion_rate:.0%}, "
                f"category: {e.edhrec.category})"
            )

    # Top recommended additions
    adds_lines = []
    for e in result.recommended_adds[:20]:
        if e.edhrec:
            adds_lines.append(
                f"  - {e.edhrec.name} (synergy: {e.edhrec.synergy:+.2f}, "
                f"inclusion: {e.edhrec.inclusion_rate:.0%}, "
                f"category: {e.edhrec.category})"
            )

    # Potential cuts
    cuts_lines = []
    for e in result.potential_cuts:
        name = e.card.name if e.card else "?"
        if e.edhrec:
            cuts_lines.append(
                f"  - {name} (synergy: {e.edhrec.synergy:+.2f}, "
                f"inclusion: {e.edhrec.inclusion_rate:.0%})"
            )
        else:
            cuts_lines.append(f"  - {name} (not in EDHREC data)")

    validated_section = "\n".join(validated_lines) if validated_lines else "  (none)"
    adds_section = "\n".join(adds_lines) if adds_lines else "  (none)"
    cuts_section = "\n".join(cuts_lines) if cuts_lines else "  (none)"

    return f"""\
Analyze this Commander deck and provide specific upgrade recommendations.

**Commander:** {result.commander_name}
**Deck:** {result.deck_name}

## Current deck cards validated by EDHREC (top synergy):
{validated_section}

## Top EDHREC recommended additions NOT currently in deck:
{adds_section}

## Cards currently in deck flagged as potential cuts:
{cuts_section}

---

Please provide:

1. **Commander Play Style** — Briefly describe what {result.commander_name} wants \
to do and the ideal game plan.

2. **Top 5 Recommended Swaps** — For each, name the specific card to CUT and the \
specific card to ADD, and explain why this swap improves the deck in terms of the \
commander's strategy. Prioritize swaps that have the biggest strategic impact.

3. **Synergy Highlights** — Call out 2-3 especially powerful synergies from the \
recommended additions that would work well with what the deck already has.

4. **Mana & Ramp Assessment** — Brief note on whether the deck's ramp package \
looks solid or needs adjustment based on the cuts/adds.

Be concise but specific. Reference actual card names and explain interactions."""


def build_evaluate_prompt(
    commander_name: str,
    deck_name: str,
    candidate_cards: list[str],
    edhrec_lookup: dict[str, EDHRECCard],
    deck_card_names: set[str],
    validated_names: list[str],
) -> str:
    """Build a prompt for evaluating a list of candidate cards."""
    card_lines = []
    for name in candidate_cards:
        norm = name.lower().strip()
        edhrec = edhrec_lookup.get(norm)
        in_deck = "YES" if norm in deck_card_names else "NO"
        if edhrec:
            card_lines.append(
                f"  - **{name}** — Currently in deck: {in_deck} | "
                f"EDHREC synergy: {edhrec.synergy:+.2f} | "
                f"Inclusion rate: {edhrec.inclusion_rate:.0%} | "
                f"Category: {edhrec.category}"
            )
        else:
            card_lines.append(
                f"  - **{name}** — Currently in deck: {in_deck} | "
                f"Not in EDHREC data for this commander"
            )

    cards_section = "\n".join(card_lines)

    validated_section = ", ".join(validated_names[:10]) if validated_names else "(none)"

    return f"""\
Evaluate these candidate cards for a Commander deck.

**Commander:** {commander_name}
**Deck:** {deck_name}

**Key cards already in the deck (validated by EDHREC):** {validated_section}

## Cards to evaluate:
{cards_section}

---

For each card, provide:

1. A **composite score (1-10)** using the weighted scoring system:
   - EDHREC Synergy (30%): Use the synergy score provided. If no data, estimate \
based on your knowledge of the card's interaction with {commander_name}.
   - Inclusion Rate (25%): Use the inclusion % provided. If no data, estimate \
based on how commonly the card appears in similar decks.
   - Strategic Fit (25%): How well does this card support {commander_name}'s game plan?
   - Mana Efficiency (20%): Cost vs. impact for this specific deck.

2. Present a **summary table** with columns: Card Name | Composite Score | Verdict \
(Must Add / Strong Add / Decent / Marginal / Skip)

3. For the top 3 scoring cards, explain **specifically what they do** in this deck \
and which existing cards they synergize with.

4. If any card is **already in the deck**, note that and say whether it should stay.

Be data-driven. Use the EDHREC statistics provided as the primary evidence."""
