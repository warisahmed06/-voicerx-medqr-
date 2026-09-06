"""
Pill Identifier fallback — for loose pills with no packaging at all.

The real system runs Computer Vision (shape, color, imprint OCR via a model
like a fine-tuned CNN or a service such as Pillbox/NIH's pill image API) on
a photo of the pill. This stub does the same *matching* step against a small
mock visual database so the API contract and frontend flow are demoable
without a trained CV model in the loop.

Swap `identify_pill()`'s body for a real inference call once a vision model
is trained/integrated — the shape/color/imprint feature extraction would sit
in front of this in a `POST /pill/photo` endpoint that runs CV first, then
calls this matcher.
"""

MOCK_PILL_DB = [
    {"shape": "round", "color": "white", "imprint": "P500", "name": "Paracetamol 500mg", "composition": "Paracetamol 500mg"},
    {"shape": "capsule", "color": "red-white", "imprint": "AMX250", "name": "Amoxicillin 250mg", "composition": "Amoxicillin Trihydrate 250mg"},
    {"shape": "oval", "color": "white", "imprint": "M500", "name": "Metformin 500mg", "composition": "Metformin Hydrochloride 500mg"},
    {"shape": "round", "color": "pink", "imprint": "C10", "name": "Cetirizine 10mg", "composition": "Cetirizine Hydrochloride 10mg"},
    {"shape": "round", "color": "yellow", "imprint": "I400", "name": "Ibuprofen 400mg", "composition": "Ibuprofen 400mg"},
]


def _similarity(a: dict, query_shape: str, query_color: str, query_imprint: str | None) -> float:
    score = 0.0
    if a["shape"].lower() == query_shape.lower():
        score += 0.4
    if a["color"].lower() == query_color.lower():
        score += 0.3
    if query_imprint and query_imprint.strip().lower() in a["imprint"].lower():
        score += 0.3
    return score


def identify_pill(shape: str, color: str, imprint: str | None) -> list[dict]:
    scored = [
        {**entry, "confidence": round(_similarity(entry, shape, color, imprint), 2)}
        for entry in MOCK_PILL_DB
    ]
    scored = [s for s in scored if s["confidence"] > 0]
    scored.sort(key=lambda x: x["confidence"], reverse=True)
    return scored[:3]
