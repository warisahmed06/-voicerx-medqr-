"""
Dynamic QR Code Generator + Digital Prescription Vault.

Every scanned prescription gets:
  - a unique ID
  - a row in a local SQLite vault (swap for Firebase/PostgreSQL in production)
  - a QR code image encoding a vault URL (not the raw data — keeps the QR
    payload small and lets the vault enforce access control / expiry later)

Scanning the QR just needs to hit `GET /prescription/vault/{id}`.
"""

import os
import io
import json
import sqlite3
import uuid
from datetime import datetime, timezone

import qrcode

from app.models import PrescriptionRecord, MedicineEntry

DB_PATH = os.getenv("VOICERX_DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "vault.db"))
BASE_URL = os.getenv("VOICERX_BASE_URL", "http://localhost:8000")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prescriptions (
            id TEXT PRIMARY KEY,
            patient_note TEXT,
            medicines_json TEXT NOT NULL,
            ocr_confidence REAL,
            raw_text TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def save_prescription(
    medicines: list[MedicineEntry],
    raw_text: str,
    ocr_confidence: float,
    patient_note: str | None = None,
) -> PrescriptionRecord:
    record_id = uuid.uuid4().hex[:10]
    created_at = datetime.now(timezone.utc).isoformat()

    conn = _get_conn()
    with conn:
        conn.execute(
            "INSERT INTO prescriptions (id, patient_note, medicines_json, ocr_confidence, raw_text, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                record_id,
                patient_note,
                json.dumps([m.model_dump() for m in medicines]),
                ocr_confidence,
                raw_text,
                created_at,
            ),
        )
    conn.close()

    return PrescriptionRecord(
        id=record_id,
        patient_note=patient_note,
        medicines=medicines,
        ocr_confidence=ocr_confidence,
        raw_text=raw_text,
        created_at=created_at,
    )


def get_prescription(record_id: str) -> PrescriptionRecord | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, patient_note, medicines_json, ocr_confidence, raw_text, created_at "
        "FROM prescriptions WHERE id = ?",
        (record_id,),
    ).fetchone()
    conn.close()

    if not row:
        return None

    rid, note, meds_json, conf, raw_text, created_at = row
    medicines = [MedicineEntry(**m) for m in json.loads(meds_json)]
    return PrescriptionRecord(
        id=rid,
        patient_note=note,
        medicines=medicines,
        ocr_confidence=conf,
        raw_text=raw_text,
        created_at=created_at,
    )


def vault_url(record_id: str) -> str:
    return f"{BASE_URL}/prescription/vault/{record_id}"


def generate_qr_png(record_id: str) -> bytes:
    """Encodes the vault URL (not raw medical data) so the QR payload stays
    small and scannable, and access can be revoked/expired server-side."""
    img = qrcode.make(vault_url(record_id))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
