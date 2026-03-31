from __future__ import annotations

import json

from flask import Flask, Response, jsonify, render_template, request

from mtg_deck_rec.analysis.comparator import compare
from mtg_deck_rec.api.client import APIError
from mtg_deck_rec.api.edhrec import fetch_recommendations
from mtg_deck_rec.api.moxfield import fetch_deck, parse_deck_id
from mtg_deck_rec.api.scryfall import card_image_url
from mtg_deck_rec.llm.client import LLMError, chat, chat_stream, is_configured
from mtg_deck_rec.llm.prompts import (
    EVALUATE_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    VISION_SYSTEM_PROMPT,
    build_analysis_prompt,
    build_evaluate_prompt,
)

import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(_BASE_DIR, "templates"),
        static_folder=os.path.join(_BASE_DIR, "static"),
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/analyze", methods=["POST"])
    def analyze():
        data = request.get_json(silent=True)
        if not data or "deck_url" not in data:
            return jsonify({"error": "Missing deck_url"}), 400

        deck_url = data["deck_url"]
        add_threshold = float(data.get("add_threshold", 0.20))
        cut_threshold = float(data.get("cut_threshold", 0.10))

        try:
            deck_id = parse_deck_id(deck_url)
            deck = fetch_deck(deck_id)
            edhrec_cards = fetch_recommendations(deck.commander.name)
            result = compare(deck, edhrec_cards, add_threshold, cut_threshold)
        except APIError as e:
            return jsonify({"error": str(e)}), 502
        except Exception as e:
            return jsonify({"error": f"Unexpected error: {e}"}), 500

        def serialize_entry(entry):
            name = entry.card.name if entry.card else (entry.edhrec.name if entry.edhrec else "?")
            scryfall_id = entry.card.scryfall_id if entry.card else None
            return {
                "name": name,
                "image_url": card_image_url(name, scryfall_id),
                "synergy": entry.edhrec.synergy if entry.edhrec else None,
                "inclusion_rate": round(entry.edhrec.inclusion_rate, 4) if entry.edhrec else None,
                "category": entry.edhrec.category if entry.edhrec else None,
                "type_line": entry.card.type_line if entry.card else "",
                "mana_cost": entry.card.mana_cost if entry.card else "",
            }

        return jsonify({
            "deck_name": result.deck_name,
            "commander": {
                "name": result.commander_name,
                "image_url": card_image_url(
                    deck.commander.name, deck.commander.scryfall_id
                ),
            },
            "mainboard_count": len(deck.mainboard),
            "edhrec_count": len(edhrec_cards),
            "validated": [serialize_entry(e) for e in result.validated],
            "recommended_adds": [serialize_entry(e) for e in result.recommended_adds],
            "potential_cuts": [serialize_entry(e) for e in result.potential_cuts],
        })

    @app.route("/api/llm-status")
    def llm_status():
        return jsonify({"configured": is_configured()})

    @app.route("/api/recommend", methods=["POST"])
    def recommend():
        """Stream LLM-generated recommendations based on comparison data."""
        data = request.get_json(silent=True)
        if not data or "deck_url" not in data:
            return jsonify({"error": "Missing deck_url"}), 400

        if not is_configured():
            return jsonify({
                "error": "LLM not configured. Set LLM_API_KEY environment variable "
                         "(or LLM_BASE_URL for Ollama)."
            }), 503

        deck_url = data["deck_url"]
        add_threshold = float(data.get("add_threshold", 0.20))
        cut_threshold = float(data.get("cut_threshold", 0.10))

        try:
            deck_id = parse_deck_id(deck_url)
            deck = fetch_deck(deck_id)
            edhrec_cards = fetch_recommendations(deck.commander.name)
            result = compare(deck, edhrec_cards, add_threshold, cut_threshold)
        except APIError as e:
            return jsonify({"error": str(e)}), 502

        user_prompt = build_analysis_prompt(result)

        def generate():
            try:
                for chunk in chat_stream(SYSTEM_PROMPT, user_prompt):
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            except LLMError as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.route("/api/identify-cards", methods=["POST"])
    def identify_cards():
        """Use vision LLM to identify MTG cards from an uploaded image."""
        if not is_configured():
            return jsonify({"error": "LLM not configured"}), 503

        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        file = request.files["image"]
        if not file.filename:
            return jsonify({"error": "Empty filename"}), 400

        import base64
        image_data = file.read()
        image_b64 = base64.b64encode(image_data).decode("ascii")

        # Determine media type
        ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpeg").lower()
        media_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        media_type = media_types.get(ext, "image/jpeg")

        try:
            result = chat(
                VISION_SYSTEM_PROMPT,
                "Identify all Magic: The Gathering cards visible in this image. "
                "Return ONLY a JSON array of card names.",
                temperature=0.1,
                max_tokens=1000,
                image_base64=image_b64,
                image_media_type=media_type,
            )
            # Parse JSON array from response
            result = result.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[-1].rsplit("```", 1)[0]
            card_names = json.loads(result)
            if not isinstance(card_names, list):
                raise ValueError("Expected a JSON array")
            return jsonify({"cards": card_names})
        except (json.JSONDecodeError, ValueError):
            return jsonify({"error": "Could not parse card names from image", "raw": result}), 422
        except LLMError as e:
            return jsonify({"error": str(e)}), 502

    @app.route("/api/evaluate-cards", methods=["POST"])
    def evaluate_cards():
        """Stream LLM evaluation of candidate cards against the current deck."""
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        if "deck_url" not in data or "cards" not in data:
            return jsonify({"error": "Missing deck_url or cards"}), 400
        if not is_configured():
            return jsonify({"error": "LLM not configured"}), 503

        candidate_cards = data["cards"]
        if not isinstance(candidate_cards, list) or not candidate_cards:
            return jsonify({"error": "cards must be a non-empty list of card names"}), 400

        deck_url = data["deck_url"]
        add_threshold = float(data.get("add_threshold", 0.20))
        cut_threshold = float(data.get("cut_threshold", 0.10))

        try:
            deck_id = parse_deck_id(deck_url)
            deck = fetch_deck(deck_id)
            edhrec_cards = fetch_recommendations(deck.commander.name)
            result = compare(deck, edhrec_cards, add_threshold, cut_threshold)
        except APIError as e:
            return jsonify({"error": str(e)}), 502

        from mtg_deck_rec.models import normalize_card_name
        # Build EDHREC lookup by normalized name
        edhrec_lookup = {normalize_card_name(c.name): c for c in edhrec_cards}
        deck_card_names = {normalize_card_name(c.name) for c in deck.mainboard}
        validated_names = [
            e.edhrec.name for e in result.validated[:10] if e.edhrec
        ]

        user_prompt = build_evaluate_prompt(
            commander_name=deck.commander.name,
            deck_name=deck.name,
            candidate_cards=candidate_cards,
            edhrec_lookup=edhrec_lookup,
            deck_card_names=deck_card_names,
            validated_names=validated_names,
        )

        def generate():
            try:
                for chunk in chat_stream(EVALUATE_SYSTEM_PROMPT, user_prompt):
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            except LLMError as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app
