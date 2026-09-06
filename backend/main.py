"""
VoiceRx & MedQR — AI-Powered Multilingual Prescription Reader,
Visual Dosing, and Dynamic QR Vault

Run locally:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Optional (for higher-accuracy OCR / better TTS in production):
    export GOOGLE_VISION_API_KEY="..."
    export OPENAI_API_KEY="..."       # enables LLM refinement of parsed prescriptions
    export GOOGLE_TTS_API_KEY="..."

Without any keys set, the app still runs end-to-end using local Tesseract
OCR + rule-based parsing + gTTS — good enough for a hackathon demo.
"""
import os
from fastapi.staticfiles import StaticFiles
_audio_cache: dict[tuple[str, str], bytes] = {}
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.ocr import run_ocr
from app.parser import parse_prescription
from app.tts import synthesize_speech, build_script, SUPPORTED_LANGS
from app.qr_vault import save_prescription, get_prescription, generate_qr_png, vault_url
from app.barcode_db import lookup_barcode
from app.pill_identifier import identify_pill
from app.voice_reminder import parse_voice_reminder
from app.models import (
    ScanResponse,
    BarcodeLookupRequest,
    BarcodeLookupResponse,
    PillIdentifyRequest,
    PillIdentifyResponse,
    PillMatch,
    VoiceReminderRequest,
    VoiceReminderResponse,
    PrescriptionRecord,
)

app = FastAPI(title="VoiceRx & MedQR API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "supported_languages": SUPPORTED_LANGS}


# ---------------------------------------------------------------------------
# Core flow: scan prescription -> OCR -> parse -> save -> QR
# ---------------------------------------------------------------------------

@app.post("/prescription/scan", response_model=ScanResponse)
async def scan_prescription(image: UploadFile = File(...), patient_note: str | None = Form(None)):
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(400, "Empty image upload")

    ocr_result = run_ocr(image_bytes)
    medicines = parse_prescription(ocr_result.text)

    record = save_prescription(
        medicines=medicines,
        raw_text=ocr_result.text,
        ocr_confidence=ocr_result.confidence,
        patient_note=patient_note,
    )

    return ScanResponse(
        prescription=record,
        qr_code_url=f"/prescription/{record.id}/qr",
        vault_url=vault_url(record.id),
    )


@app.get("/prescription/vault/{record_id}", response_model=PrescriptionRecord)
async def get_from_vault(record_id: str):
    record = get_prescription(record_id)
    if not record:
        raise HTTPException(404, "Prescription not found — QR code may be invalid or expired")
    return record


@app.get("/prescription/{record_id}/qr")
async def get_qr_code(record_id: str):
    record = get_prescription(record_id)
    if not record:
        raise HTTPException(404, "Prescription not found")
    png_bytes = generate_qr_png(record_id)
    return Response(content=png_bytes, media_type="image/png")


@app.get("/prescription/{record_id}/audio")
async def get_audio(record_id: str, lang: str = "en"):
    record = get_prescription(record_id)
    if not record:
        raise HTTPException(404, "Prescription not found")

    audio_bytes = synthesize_speech(record.medicines, lang=lang)
    if not audio_bytes:
        # TTS unavailable (no network / missing deps) — surface the script
        # as text so the demo can still show what would have been spoken.
        script = build_script(record.medicines)
        raise HTTPException(503, f"TTS unavailable. Spoken script would be: {script}")

    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.get("/prescription/{record_id}/script")
async def get_script(record_id: str, lang: str = "en"):
    """Text version of what the TTS would say — useful for debugging /
    displaying alongside the audio player in the UI."""
    record = get_prescription(record_id)
    if not record:
        raise HTTPException(404, "Prescription not found")
    return {"script": build_script(record.medicines), "lang": lang}


# ---------------------------------------------------------------------------
# Fallbacks for medicines without a VoiceRx QR code
# ---------------------------------------------------------------------------

@app.post("/medicine/barcode", response_model=BarcodeLookupResponse)
async def barcode_lookup(req: BarcodeLookupRequest):
    info = lookup_barcode(req.barcode)
    if not info:
        return BarcodeLookupResponse(found=False)
    return BarcodeLookupResponse(found=True, **info)


@app.post("/medicine/pill-identify", response_model=PillIdentifyResponse)
async def pill_identify(req: PillIdentifyRequest):
    matches = identify_pill(req.shape, req.color, req.imprint)
    return PillIdentifyResponse(
        matches=[PillMatch(name=m["name"], confidence=m["confidence"], composition=m["composition"]) for m in matches]
    )


@app.post("/reminder/voice", response_model=VoiceReminderResponse)
async def voice_reminder(req: VoiceReminderRequest):
    return parse_voice_reminder(req.transcript, req.lang)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")