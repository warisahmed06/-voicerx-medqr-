"""
Manual Voice Input fallback — lets a user set a reminder by voice for a
medicine that has no OCR'd prescription, no barcode, and no visible imprint
(e.g. "Remind me to take my BP tablet every morning and night").

Takes an already-transcribed string (device/browser STT does the audio-to-text
step; this module only does the intent parsing) and extracts a medicine name
and time-of-day slots.
"""

import re
from app.models import VoiceReminderResponse

TIME_KEYWORDS = {
    "morning": "☀️",
    "afternoon": "🌤️",
    "evening": "🌇",
    "night": "🌙",
    "bedtime": "🌙",
}


def parse_voice_reminder(transcript: str, lang: str = "en") -> VoiceReminderResponse:
    text = transcript.lower().strip()

    times_found = [label for label in TIME_KEYWORDS if label in text]

    # Very simple medicine-name heuristic: text after "take my"/"take"/"for"
    # up to the next time keyword or end of string. A production version
    # would run this through the same LLM used in parser.py for robustness.
    medicine = None
    match = re.search(r"take (?:my |the )?([a-z0-9 ]+?)(?:\s+(?:every|at|in the|" + "|".join(TIME_KEYWORDS) + r")|$)", text)
    if match:
        medicine = match.group(1).strip()

    if not medicine and not times_found:
        return VoiceReminderResponse(
            medicine=None,
            time_of_day=[],
            reminder_created=False,
            message="Sorry, I couldn't understand a medicine name or time. Please try again, "
                    "e.g. 'Remind me to take my BP tablet every morning and night'.",
        )

    icons = [TIME_KEYWORDS[t] for t in times_found]
    summary = f"Reminder set for {medicine or 'your medicine'}" + (
        f" at: {' '.join(icons)}" if icons else " (time not specified — defaulting to morning)"
    )

    return VoiceReminderResponse(
        medicine=medicine,
        time_of_day=times_found or ["morning"],
        reminder_created=True,
        message=summary,
    )
