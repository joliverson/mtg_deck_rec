# MTG Deck Rec

Compare your Magic: The Gathering Commander deck against EDHREC recommendations. Paste a Moxfield deck URL, and get data-driven suggestions for cards to add, cards to cut, and AI-powered analysis.

## Features

- **Deck Analysis** — Fetches your Moxfield deck and compares it against EDHREC's aggregated data for your commander
- **Card Recommendations** — Identifies high-synergy cards you're missing and flags low-inclusion cards to consider cutting
- **Web UI** — Dark-themed interface with card imagery from Scryfall, tabbed results, and card detail modals
- **AI Deck Advisor** — Streaming LLM-powered recommendations with strategic analysis (OpenAI or local Ollama)
- **Card Evaluation** — Evaluate candidate cards via image upload, file upload, or text input with weighted scoring (synergy, inclusion rate, strategic fit, mana efficiency)
- **CLI Mode** — Terminal-based output for quick analysis without a browser

## Quick Start

```bash
# Clone
git clone https://github.com/joliverson/mtg_deck_rec.git
cd mtg_deck_rec

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install
pip install -e .

# Run web UI
python3 -m mtg_deck_rec --web --port 5050
```

Then open http://localhost:5050 and paste a Moxfield deck URL.

## Configuration

Create a `.env` file in the project root for AI features:

```env
LLM_API_KEY=your-openai-api-key
LLM_MODEL=gpt-4o-mini
```

For local Ollama instead of OpenAI:

```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3
```

The AI features (Deck Advisor, Card Evaluation) are optional — deck analysis works without an LLM key.

## Usage

### Web UI

```bash
python3 -m mtg_deck_rec --web --port 5050
```

### CLI

```bash
# Analyze a deck
python3 -m mtg_deck_rec https://moxfield.com/decks/e2o8jxOWuUmM9mQin03kmQ

# Adjust thresholds
python3 -m mtg_deck_rec <deck_url> --add-threshold 0.30 --cut-threshold 0.15

# JSON output
python3 -m mtg_deck_rec <deck_url> --json
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--web` | — | Launch web UI |
| `--port` | 5000 | Web UI port |
| `--add-threshold` | 0.20 | Min EDHREC inclusion rate to recommend adding |
| `--cut-threshold` | 0.10 | Inclusion rate below which to flag as potential cut |
| `--top-n` | 25 | Max cards shown per section |
| `--json` | — | Output raw JSON |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web UI |
| POST | `/api/analyze` | Analyze deck vs EDHREC |
| GET | `/api/llm-status` | Check LLM configuration |
| POST | `/api/recommend` | Stream AI recommendations (SSE) |
| POST | `/api/identify-cards` | Identify cards from image (vision LLM) |
| POST | `/api/evaluate-cards` | Stream card evaluation scores (SSE) |

## Project Structure

```
mtg_deck_rec/
├── cli.py              # CLI entry point
├── models.py           # Card, Deck, EDHRECCard dataclasses
├── api/
│   ├── client.py       # Rate-limited HTTP client
│   ├── moxfield.py     # Moxfield API v3
│   ├── edhrec.py       # EDHREC JSON API
│   └── scryfall.py     # Scryfall image URLs
├── analysis/
│   └── comparator.py   # Deck vs EDHREC comparison engine
├── display/
│   └── terminal.py     # CLI formatted output
├── llm/
│   ├── client.py       # OpenAI-compatible streaming client
│   └── prompts.py      # MTG-specific prompt engineering
└── web/
    └── app.py          # Flask web app
```

## Data Sources

- **[Moxfield](https://moxfield.com)** — Deck lists
- **[EDHREC](https://edhrec.com)** — Commander metagame data
- **[Scryfall](https://scryfall.com)** — Card images

## Requirements

- Python 3.11+
- Flask 3.0+
- OpenAI API key (optional, for AI features)
