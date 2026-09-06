"""
Maps medical shorthand frequency codes to plain-language labels and visual
dosing icons, so non-literate or low-literacy users can follow a schedule
without reading text.
"""

# code -> (human label, list of time-of-day icons)
FREQUENCY_MAP: dict[str, tuple[str, list[str]]] = {
    "OD": ("Once a day", ["☀️"]),
    "BD": ("Twice a day", ["☀️", "🌙"]),
    "BID": ("Twice a day", ["☀️", "🌙"]),
    "TID": ("Three times a day", ["☀️", "🌤️", "🌙"]),
    "TDS": ("Three times a day", ["☀️", "🌤️", "🌙"]),
    "QID": ("Four times a day", ["☀️", "🌤️", "🌇", "🌙"]),
    "QDS": ("Four times a day", ["☀️", "🌤️", "🌇", "🌙"]),
    "HS": ("At bedtime", ["🌙"]),
    "SOS": ("As needed", ["⚠️"]),
    "STAT": ("Immediately", ["⏱️"]),
    "AC": ("Before meals", ["🍽️➡️"]),
    "PC": ("After meals", ["➡️🍽️"]),
    "QOD": ("Every other day", ["📅"]),
    "Q4H": ("Every 4 hours", ["⏰"]),
    "Q6H": ("Every 6 hours", ["⏰"]),
    "Q8H": ("Every 8 hours", ["⏰"]),
}

FOOD_ICON = {
    "before food": "🍽️➡️",
    "after food": "➡️🍽️",
    "with food": "🍽️",
    "empty stomach": "🚫🍽️",
}


def resolve_frequency(code: str) -> tuple[str, list[str]]:
    """Look up a frequency shorthand code; falls back gracefully for unknowns."""
    code = code.strip().upper().replace(".", "")
    if code in FREQUENCY_MAP:
        return FREQUENCY_MAP[code]
    return (code or "As directed", ["❓"])


def food_instruction_icon(instruction: str | None) -> str | None:
    if not instruction:
        return None
    return FOOD_ICON.get(instruction.lower())
