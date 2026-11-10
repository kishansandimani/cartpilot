"""Gemini REST client (https://ai.google.dev/api/generate-content).

Two jobs:
  1. extract_requirements() - turn chat into a structured product search.
  2. rank_products()       - explain which of the REAL products found fit best.
The model only sees product data that came from the provider and may only pick from it.

Reliability: temporary errors are retried, an optional GEMINI_FALLBACK_MODEL is tried,
and each call is capped at TOTAL_BUDGET_SECONDS so the app never hangs.
"""
import json
import re
import time
from decimal import Decimal
from typing import Optional

import httpx

from ..config import get_settings

RETRY_STATUS = {429, 500, 502, 503, 504}
ATTEMPTS_PER_MODEL = 2
TOTAL_BUDGET_SECONDS = 30  # never wait longer than this per Gemini call


class GeminiError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _call(system: str, contents: list[dict], *, temperature: float = 0.2) -> dict:
    s = get_settings()
    if not s.gemini_api_key:
        raise GeminiError("GEMINI_API_KEY is not set. Add it to backend/.env to enable the AI assistant.", 503)

    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"},
    }
    models = [s.gemini_model] + ([s.gemini_fallback_model] if s.gemini_fallback_model else [])
    deadline = time.monotonic() + TOTAL_BUDGET_SECONDS
    last_error = "unknown error"

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(ATTEMPTS_PER_MODEL):
            remaining = deadline - time.monotonic()
            if remaining < 2:
                raise GeminiError(f"The AI service is busy right now. ({last_error})", 503)
            try:
                r = httpx.post(url, json=body, headers={"x-goog-api-key": s.gemini_api_key},
                               timeout=min(15, remaining))
            except httpx.HTTPError as e:
                last_error = f"Could not reach Gemini ({model}): {type(e).__name__}"
            else:
                if r.status_code == 200:
                    try:
                        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    except (KeyError, IndexError):
                        raise GeminiError("Gemini returned an empty answer (it may have been blocked). Try rephrasing.")
                    return parse_json_loose(text)
                last_error = f"Gemini ({model}) returned HTTP {r.status_code}: {r.text[:150]}"
                if r.status_code not in RETRY_STATUS:
                    raise GeminiError(last_error)  # 400/403/404: retrying will not help
            if attempt < ATTEMPTS_PER_MODEL - 1:
                time.sleep(1)

    raise GeminiError(f"The AI service is busy right now. Please try again in a moment. ({last_error})", 503)


def parse_json_loose(text: str) -> dict:
    """Parses JSON even if the model wrapped it in ```json fences."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise GeminiError("Gemini returned text that is not valid JSON. Please try again.")
    if not isinstance(data, dict):
        raise GeminiError("Gemini returned an unexpected JSON shape.")
    return data


EXTRACT_SYSTEM = """You are the requirement extractor of CartPilot AI, a shopping assistant.
Read the conversation and return ONLY JSON with exactly these keys:
{"needs_clarification": boolean,
 "clarifying_question": string|null,   // ask ONE short question only if you cannot search yet (e.g. no product type)
 "search_query": string|null,          // short product search text, e.g. "laptop programming"
 "max_price": number|null, "min_price": number|null,
 "currency": string|null,              // ISO code the user used (INR for rupees / Rs / ₹, USD for $)
 "brand": string|null, "category": string|null,
 "must_have": [string], "preferences": [string],
 "wants_comparison": boolean}
Never invent a budget or brand the user did not state. If the user writes in Hindi or Kannada, answer clarifying questions in that language."""

RANK_SYSTEM = """You are CartPilot AI. You get the user's requirements and a JSON list of REAL products
(already fetched from a store API). Pick the best matches and explain them.
RULES: use ONLY facts present in the list. Never invent specs, ratings, prices or availability.
If a spec the user cares about is missing from the data, say it is not listed.
Return ONLY JSON: {"summary": string,
 "recommendations": [{"product_id": number, "why": string, "pros": [string], "cons": [string]}]}
Order from best to worst. At most 5. Reply in the user's language."""

EXPLAIN_SYSTEM = """You are CartPilot AI. Explain in 2-4 sentences, using ONLY the provided facts, why this product
was recommended for the user's request. Return JSON: {"explanation": string}."""

INSIGHT_SYSTEM = """You are CartPilot AI. You receive aggregated spending numbers (already computed).
Write 3-5 short, useful observations for the user. Use ONLY the numbers given; do not invent anything.
Return JSON: {"insights": [string]}."""


def extract_requirements(history: list[dict], user_message: str, saved_preferences: dict) -> dict:
    contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in history[-10:]]
    pref_note = f"\n(Saved user preferences, use only if relevant: {json.dumps(saved_preferences)})" if saved_preferences else ""
    contents.append({"role": "user", "parts": [{"text": user_message + pref_note}]})
    data = _call(EXTRACT_SYSTEM, contents, temperature=0.1)

    def num(v) -> Optional[Decimal]:
        try:
            return Decimal(str(v)) if v is not None else None
        except Exception:
            return None

    return {
        "needs_clarification": bool(data.get("needs_clarification")),
        "clarifying_question": data.get("clarifying_question"),
        "search_query": data.get("search_query"),
        "max_price": num(data.get("max_price")), "min_price": num(data.get("min_price")),
        "currency": (data.get("currency") or None) and str(data["currency"]).upper(),
        "brand": data.get("brand"), "category": data.get("category"),
        "must_have": [str(x) for x in data.get("must_have") or []],
        "preferences": [str(x) for x in data.get("preferences") or []],
        "wants_comparison": bool(data.get("wants_comparison")),
    }


def rank_products(user_message: str, requirements: dict, products: list[dict]) -> dict:
    slim = [{"product_id": p["id"], "title": p["title"], "brand": p.get("brand"), "price": str(p["price"]),
             "currency": p["currency"], "merchant": p.get("merchant"), "availability": p.get("availability"),
             "rating": p.get("rating"), "specs": p.get("specs")} for p in products]
    req = {k: (str(v) if isinstance(v, Decimal) else v) for k, v in requirements.items()}
    prompt = f"User request: {user_message}\nRequirements: {json.dumps(req)}\nProducts: {json.dumps(slim)}"
    data = _call(RANK_SYSTEM, [{"role": "user", "parts": [{"text": prompt}]}])
    valid_ids = {p["id"] for p in products}
    recs = []
    for r in data.get("recommendations") or []:
        try:
            pid = int(r.get("product_id"))
        except (TypeError, ValueError):
            continue
        if pid in valid_ids:  # drop anything the model made up
            recs.append({"product_id": pid, "why": str(r.get("why", "")),
                         "pros": [str(x) for x in r.get("pros") or []], "cons": [str(x) for x in r.get("cons") or []]})
    return {"summary": str(data.get("summary", "")), "recommendations": recs}


def explain_recommendation(user_request: str, product: dict, reason: Optional[str]) -> str:
    prompt = json.dumps({"user_request": user_request, "product": product, "earlier_reason": reason}, default=str)
    return str(_call(EXPLAIN_SYSTEM, [{"role": "user", "parts": [{"text": prompt}]}]).get("explanation", ""))


def narrate_insights(aggregates: dict) -> list[str]:
    data = _call(INSIGHT_SYSTEM, [{"role": "user", "parts": [{"text": json.dumps(aggregates, default=str)}]}])
    return [str(x) for x in data.get("insights") or []]