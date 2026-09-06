"""Pydantic schemas shared across the VoiceRx & MedQR API."""

from typing import Optional
from pydantic import BaseModel


class MedicineEntry(BaseModel):
    name: str
    dosage: Optional[str] = None          # e.g. "500mg"
    frequency_code: Optional[str] = None  # e.g. "BD", "TID", "OD", "HS", "SOS"
    frequency_label: str                  # human-readable, e.g. "Twice a day"
    duration: Optional[str] = None        # e.g. "5 days"
    food_instruction: Optional[str] = None  # "before food" / "after food" / None
    icons: list[str]                      # e.g. ["☀️", "🌙"]
    raw_line: str                         # original OCR line this was parsed from


class PrescriptionRecord(BaseModel):
    id: str
    patient_note: Optional[str] = None
    medicines: list[MedicineEntry]
    ocr_confidence: float
    raw_text: str
    created_at: str


class ScanResponse(BaseModel):
    prescription: PrescriptionRecord
    qr_code_url: str
    vault_url: str


class BarcodeLookupRequest(BaseModel):
    barcode: str


class BarcodeLookupResponse(BaseModel):
    found: bool
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    composition: Optional[str] = None
    standard_dosage: Optional[str] = None


class PillIdentifyRequest(BaseModel):
    shape: str      # "round", "oval", "capsule", "oblong"
    color: str      # "white", "yellow", "pink", ...
    imprint: Optional[str] = None  # text/number embossed on pill


class PillMatch(BaseModel):
    name: str
    confidence: float
    composition: str


class PillIdentifyResponse(BaseModel):
    matches: list[PillMatch]


class VoiceReminderRequest(BaseModel):
    transcript: str  # already-transcribed text from device STT
    lang: str = "en"


class VoiceReminderResponse(BaseModel):
    medicine: Optional[str] = None
    time_of_day: list[str]
    reminder_created: bool
    message: str
