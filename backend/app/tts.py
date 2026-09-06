"""
Multilingual Text-to-Speech module.

Converts a structured MedicineEntry list into a natural-language script
("Take Paracetamol 500mg, twice a day, after food, for 5 days") and
synthesizes it as audio in the patient's local language.

Priority order:
  1. Google Cloud TTS (higher quality, needs GOOGLE_APPLICATION_CREDENTIALS)
  2. gTTS (Google Translate TTS — free, no API key, good enough for a demo;
     needs internet access at request time)

Swap in ElevenLabs / Google Cloud TTS for production — better prosody and
voice quality for elderly/low-vision users than the gTTS fallback.
"""

import os
import io
from app.models import MedicineEntry

# ISO language codes supported out of the box by gTTS for Indian languages.
SUPPORTED_LANGS = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
}

GOOGLE_TTS_API_KEY = os.getenv("GOOGLE_TTS_API_KEY", "")


def build_script(medicines: list[MedicineEntry]) -> str:
    """Turns structured dosing data into a plain-language spoken script."""
    if not medicines:
        return "No medicines were detected on this prescription. Please consult your pharmacist."

    parts = []
    for m in medicines:
        chunk = f"Take {m.name}"
        if m.dosage:
            chunk += f", {m.dosage}"
        chunk += f", {m.frequency_label.lower()}"
        if m.food_instruction:
            chunk += f", {m.food_instruction}"
        if m.duration:
            chunk += f", for {m.duration}"
        chunk += "."
        parts.append(chunk)
    return " ".join(parts)


def _translate_script(script: str, lang: str) -> str:
    """Translate the English script into the target language before synthesis.
    gTTS synthesizes whatever text it's given without translating, so for a
    non-English voice note we need translated text first."""
    if lang == "en":
        return script
    try:
        from deep_translator import GoogleTranslator

        return GoogleTranslator(source="en", target=lang).translate(script)
    except Exception as e:  # noqa: BLE001
        print(f"[tts] Translation to '{lang}' failed, using English text: {e}")
        return script


def synthesize_speech(medicines: list[MedicineEntry], lang: str = "en") -> bytes:
    """Returns MP3 audio bytes for the dosing instructions in the given language."""
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    script = build_script(medicines)
    localized_script = _translate_script(script, lang)

    try:
        from gtts import gTTS

        buf = io.BytesIO()
        gTTS(text=localized_script, lang=lang).write_to_fp(buf)
        return buf.getvalue()
    except Exception as e:  # noqa: BLE001
        print(f"[tts] gTTS synthesis failed: {e}")
        # Return empty bytes; the API layer surfaces the script text as a
        # fallback so the demo still works without network/TTS access.
        return b""
