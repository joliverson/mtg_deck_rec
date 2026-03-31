"""Scryfall image URL helpers. No API calls needed — uses CDN directly."""

from __future__ import annotations

import urllib.parse


def card_image_url(name: str, scryfall_id: str | None = None, version: str = "normal") -> str:
    """Get a Scryfall card image URL.

    If we have a scryfall_id, use the direct image endpoint (fast, no redirect).
    Otherwise fall back to the named card redirect endpoint.
    """
    if scryfall_id:
        return f"https://api.scryfall.com/cards/{scryfall_id}?format=image&version={version}"
    encoded = urllib.parse.quote(name)
    return f"https://api.scryfall.com/cards/named?exact={encoded}&format=image&version={version}"
