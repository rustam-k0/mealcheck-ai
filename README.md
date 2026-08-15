# BiteMate — food photo diary 🍽

A focused Telegram bot for approximate meal recognition from photos, text, and voice. It first shows editable foods and portions, calculates calories and protein/fat/carbohydrates only after explicit confirmation, and can save the confirmed result to a local diary.

## Product flow

Send a photo directly—no menu step is required—or describe a meal in text/voice. Banana Mate extracts a structured composition and offers **Correct / Confirm / Cancel** without asking clarification questions. Confirmation starts a second structured AI call for an approximate itemized nutrition result, uncertainty range, and reasons. Saving to the diary is a separate explicit action.

The bot does not diagnose, prescribe treatment or medical diets, moralize food, or support purging and extreme restriction. Photo estimates are inherently imprecise: exact weights, hidden oil, sauces, recipes, and cooking method can materially change the result.

## Setup

Requires Python 3.11+, a Telegram bot token, and an OpenAI-compatible aggregator or private gateway:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

The supplied example is configured for OpenCode Go using its OpenAI-compatible Chat Completions endpoint. Add your OpenCode Go key locally or as a deployment secret; never commit it:

```env
AI_API_KEY=your_opencode_go_key
AI_BASE_URL=https://opencode.ai/zen/go/v1
AI_PROVIDER=opencode-go
AI_VISION_MODEL=mimo-v2.5
AI_TEXT_MODEL=mimo-v2.5-pro
AI_TRANSCRIPTION_MODEL=mimo-v2.5
AI_MODEL_CATALOG=mimo-v2.5|text+image+audio,mimo-v2.5-pro|text
```

Routing is automatic and hidden from the Telegram UI: `mimo-v2.5` handles compressed photos and direct audio input, while `mimo-v2.5-pro` handles text extraction, corrections, and nutrition calculation. This design does **not** claim one key works directly across OpenAI, xAI, and Google; cross-provider routing must be provided by the configured gateway.

Catalog entries use `model|text+image`, `model|text`, or `model|text+image+audio`. Users can only select catalog models. A selected text-only model is never silently replaced for a photo; the bot asks the user to select a multimodal model.

Voice is optional. Set `AI_TRANSCRIPTION_MODEL`; if transcription uses another service, also set `TRANSCRIPTION_API_KEY` and `TRANSCRIPTION_BASE_URL`. Without it, text and photo flows start normally and voice gets a clear fallback message. A local transcription implementation can later be injected behind the same adapter boundary.

## Storage and operation

Telegram FSM stores structured unconfirmed `MealDraft` objects. With `REDIS_URL`, they survive process restarts; without it, memory storage is used. Confirmed diary entries use SQLite (`DIARY_DB_PATH`) behind `DiaryRepository`, ready for a PostgreSQL implementation. Resetting an analysis clears the draft, never diary records.

Polling and webhook modes, `/healthz`, access control, rate limiting, safe structured logs, metrics, error handling, long-message helpers, and RU/EN UI remain. Logs intentionally exclude API keys, prompts, request contents, photo bytes, and transcriptions. Operators should still publish a privacy notice covering Telegram and their chosen AI gateway, retention, and deletion.

## Architecture

- `routers/`: Telegram interaction only
- `services/ai.py`: shared photo/text/voice-after-transcription pipeline
- `adapters/unified.py`: configurable OpenAI-compatible API
- `domain.py`: validated food, draft, nutrition, and diary models
- `diary.py`: repository interface and SQLite implementation
- `services/safety.py`: medical/eating-disorder guardrails
- `states.py`: explicit confirmation and diary states

Run tests with `python -m pytest -q`. Tests use fake adapters and do not spend API credits.
