"""
AI Medical Parsing Module.

Turns raw OCR text (often messy: line breaks in odd places, shorthand,
inconsistent spacing) into structured MedicineEntry records.

Two-stage approach:
  1. Regex/rule-based extraction — fast, free, works offline, handles the
     common shorthand vocabulary (OD/BD/TID/HS/SOS/AC/PC + dosage units).
  2. Optional LLM refinement pass — if OPENAI_API_KEY is set, the raw OCR
     text and the rule-based draft are sent to an LLM to fix parsing errors
     rule-based regex can't handle (line-wrap artifacts, unusual abbreviations,
     doctor-specific shorthand). This is the "AI Medical Parsing Module" the
     architecture diagram refers to — rules alone are a strong offline fallback.
"""

import os
import re
import json
from app.models import MedicineEntry
from app.dosing_icons import resolve_frequency, food_instruction_icon

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

FREQ_PATTERN = re.compile(
    r"\b(OD|BD|BID|TID|TDS|QID|QDS|HS|SOS|STAT|AC|PC|QOD|Q4H|Q6H|Q8H)\b",
    re.IGNORECASE,
)
DOSAGE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?\s?(?:mg|ml|mcg|g|IU|units?))\b", re.IGNORECASE)
DURATION_PATTERN = re.compile(r"\b(\d+\s?(?:day|days|week|weeks|month|months))\b", re.IGNORECASE)
FOOD_PATTERN = re.compile(
    r"\b(before food|after food|with food|empty stomach|A\.?C\.?|P\.?C\.?)\b",
    re.IGNORECASE,
)


def _food_instruction_from_text(line: str) -> str | None:
    m = FOOD_PATTERN.search(line)
    if not m:
        return None
    token = m.group(1).lower().replace(".", "")
    if token in ("ac",):
        return "before food"
    if token in ("pc",):
        return "after food"
    return token


def _rule_based_parse(raw_text: str) -> list[MedicineEntry]:
    entries: list[MedicineEntry] = []
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    for line in lines:
        freq_match = FREQ_PATTERN.search(line)
        dosage_match = DOSAGE_PATTERN.search(line)
        duration_match = DURATION_PATTERN.search(line)
        food_instruction = _food_instruction_from_text(line)

        # A line only counts as a medicine line if it has at least a
        # frequency or dosage marker — otherwise it's likely a header,
        # patient name, or date line.
        if not freq_match and not dosage_match:
            continue

        freq_code = freq_match.group(1).upper() if freq_match else None
        freq_label, icons = resolve_frequency(freq_code) if freq_code else (
            "As directed", ["❓"]
        )

        food_icon = food_instruction_icon(food_instruction)
        if food_icon:
            icons = icons + [food_icon]

        # Medicine name heuristic: text before the first marker on the line.
        cut_points = [m.start() for m in [freq_match, dosage_match, duration_match] if m]
        name_end = min(cut_points) if cut_points else len(line)
        name = line[:name_end].strip(" -:\t")
        name = re.sub(r"^\d+[\).]?\s*", "", name)  # strip leading "1." numbering

        entries.append(
            MedicineEntry(
                name=name or "Unrecognized medicine",
                dosage=dosage_match.group(1) if dosage_match else None,
                frequency_code=freq_code,
                frequency_label=freq_label,
                duration=duration_match.group(1) if duration_match else None,
                food_instruction=food_instruction,
                icons=icons,
                raw_line=line,
            )
        )

    return entries


def _llm_refine(raw_text: str, draft: list[MedicineEntry]) -> list[MedicineEntry]:
    """Optional refinement pass using an LLM to catch what regex misses.
    Falls back silently to the rule-based draft if no API key or on error."""
    if not OPENAI_API_KEY:
        return draft

    import httpx

    draft_json = json.dumps([d.model_dump() for d in draft])
    prompt = f"""You are a medical prescription parser. Given raw OCR text from a
handwritten/printed prescription and a rule-based draft parse, correct and complete
the structured medicine list. Fix OCR errors, merge lines that got split incorrectly,
and infer missing dosage/frequency/duration where clearly implied by context.

Return ONLY a JSON array of objects with keys: name, dosage, frequency_code,
frequency_label, duration, food_instruction, raw_line. No prose, no markdown fences.

Raw OCR text:
{raw_text}

Rule-based draft:
{draft_json}
"""
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        content = re.sub(r"^```json|```$", "", content.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(content)

        refined: list[MedicineEntry] = []
        for item in parsed:
            freq_code = (item.get("frequency_code") or "").upper() or None
            freq_label, icons = (
                resolve_frequency(freq_code) if freq_code
                else (item.get("frequency_label", "As directed"), ["❓"])
            )
            food_icon = food_instruction_icon(item.get("food_instruction"))
            if food_icon:
                icons = icons + [food_icon]
            refined.append(
                MedicineEntry(
                    name=item.get("name", "Unrecognized medicine"),
                    dosage=item.get("dosage"),
                    frequency_code=freq_code,
                    frequency_label=freq_label,
                    duration=item.get("duration"),
                    food_instruction=item.get("food_instruction"),
                    icons=icons,
                    raw_line=item.get("raw_line", ""),
                )
            )
        return refined or draft
    except Exception as e:  # noqa: BLE001 — LLM refinement is best-effort
        print(f"[parser] LLM refinement failed, using rule-based draft: {e}")
        return draft


def parse_prescription(raw_text: str) -> list[MedicineEntry]:
    draft = _rule_based_parse(raw_text)
    return _llm_refine(raw_text, draft)
