"""
Barcode Scanner fallback — looks up medicine details from a pharmaceutical
database when a strip/pack has a standard barcode but no VoiceRx QR code.

This ships with a small mock dataset (data/mock_medicines.json) so the demo
works offline. In production, point BARCODE_DB_API_URL at a real pharma
database (e.g. a licensed NDC/GS1 dataset or a national drug registry API).
"""

import os
import json
import httpx

BARCODE_DB_API_URL = os.getenv("BARCODE_DB_API_URL", "")
MOCK_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_medicines.json")


def _load_mock_db() -> dict:
    with open(MOCK_DB_PATH) as f:
        return json.load(f)


def lookup_barcode(barcode: str) -> dict | None:
    if BARCODE_DB_API_URL:
        try:
            resp = httpx.get(f"{BARCODE_DB_API_URL}/{barcode}", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:  # noqa: BLE001
            print(f"[barcode] External DB lookup failed, using mock DB: {e}")

    db = _load_mock_db()
    return db.get(barcode)
