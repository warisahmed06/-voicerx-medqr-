# VoiceRx & MedQR — Prototype

AI-Powered Multilingual Prescription Reader, Visual Dosing, and Dynamic QR Vault

## What's included

**Backend** (`backend/`) — FastAPI service implementing every module from the architecture:

| Module | File | What it does |
|---|---|---|
| OCR Engine | `app/ocr.py` | Google Vision API / AWS Textract with local Tesseract fallback (works offline, no key needed) |
| AI Medical Parsing | `app/parser.py` | Regex-based shorthand parsing (OD/BD/TID/HS/SOS/AC/PC...) + optional LLM refinement pass |
| Visual Dosing Icons | `app/dosing_icons.py` | Maps frequency codes → ☀️🌤️🌙 schedules for non-literate users |
| Multilingual TTS | `app/tts.py` | Builds a natural-language script, translates it, and synthesizes speech (gTTS, swappable for Google Cloud TTS / ElevenLabs) |
| Dynamic QR + Vault | `app/qr_vault.py` | SQLite-backed prescription vault + QR code generation |
| Barcode fallback | `app/barcode_db.py` | Mock pharma DB lookup (swap for a real NDC/GS1/national registry) |
| Pill identifier fallback | `app/pill_identifier.py` | Shape/color/imprint matcher stub (swap for a trained CV model) |
| Voice reminder fallback | `app/voice_reminder.py` | Parses a transcript into medicine + time-of-day reminder |

**Frontend** (`frontend/index.html`) — Single-page UI with four tabs: Scan Prescription, Barcode Lookup, Pill Identifier, Voice Reminder. No build step.

This is a **working skeleton** for the hackathon demo round — every endpoint runs end-to-end without any API keys (using local/free fallbacks), and every module has a clear "swap this for production" note in its docstring.

## Quick start

```bash
cd backend
pip install -r requirements.txt

# Local OCR needs the Tesseract binary installed on the system:
#   Ubuntu/Debian: sudo apt-get install tesseract-ocr
#   Mac:           brew install tesseract

uvicorn main:app --reload --port 8000
```

Then open `frontend/index.html` in a browser (or serve it: `python -m http.server 5500` from `frontend/`).

### Optional — higher accuracy / production APIs

```bash
export GOOGLE_VISION_API_KEY="..."   # much better handwriting OCR than local Tesseract
export OPENAI_API_KEY="..."          # enables LLM refinement of parsed prescriptions
export GOOGLE_TTS_API_KEY="..."      # higher-quality voice than gTTS (wiring left as a TODO in tts.py)
```

### Try it

1. **Scan Rx tab** — upload any photo of a prescription (or a printed medicine list — Tesseract handles print far better than handwriting). See parsed medicines with dosing icons, play the audio instructions, view the QR code.
2. **Barcode tab** — try sample codes `8901234567890`–`8901234567893` from the mock DB.
3. **Pill ID tab** — pick shape/color, e.g. round + white + "P500" → matches Paracetamol.
4. **Voice Reminder tab** — type e.g. *"Remind me to take my BP tablet every morning and night"*.

## Architecture (as implemented)

```
[Prescription Image]
        │
        ▼
 OCR Engine (Cloud Vision/Textract → local Tesseract fallback)
        │
        ▼
 AI Medical Parsing Module (regex rules → optional LLM refinement)
        │
   ┌────┴─────────────────────────────┐
   ▼                                  ▼
 Multilingual TTS              Dynamic QR Generator
 (script → translate → gTTS)   (vault URL encoded, not raw data)
   │                                  │
   ▼                                  ▼
 Visual Dosing Icons UI        SQLite Prescription Vault
                                (shareable via QR scan)

 Fallbacks (no QR / no packaging):
   Barcode → mock pharma DB      Pill photo → shape/color/imprint matcher
   No barcode either → manual voice input reminder
```

## Known limitations in this prototype (flagged honestly)

- **Regex parser picks the first frequency match per line** — a line with two codes (e.g. "OD HS") only captures one. The LLM refinement pass (when `OPENAI_API_KEY` is set) is meant to catch this; without it, rule-based parsing is a reasonable but imperfect fallback.
- **OCR accuracy on real handwriting** will be poor with local Tesseract — this is expected; the module is built so swapping in Cloud Vision (better at handwriting) is a one-line env var, no code change.
- **Pill identifier and barcode DB are mock datasets** (4-5 entries) for demo purposes — production needs a licensed pharmaceutical database.
- **QR payload is a vault URL, not encrypted JSON** as the original architecture sketch suggested — this is deliberately safer (revocable/expirable server-side, no raw medical data sitting in a scannable code) but is a design choice worth mentioning if judges ask about the deviation.

## What to build next

1. Wire a real trained CV model for the pill identifier (photo upload → shape/color/imprint extraction happens automatically instead of manual dropdowns).
2. Add authentication + role-based access to the vault (pharmacist vs. patient views).
3. Mobile app wrapper (Flutter/React Native) around this API, with on-device STT for the voice reminder flow instead of typed transcripts.
4. Push notification / SMS reminders scheduled from the parsed dosing schedule.
5. Encrypt vault contents at rest and add QR expiry for medical-record privacy compliance.
