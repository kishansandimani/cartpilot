"""Quick test: is Gemini or Channel3 the slow one? Run:  python check_services.py"""
import time
import httpx
from app.config import get_settings

s = get_settings()


def timed(label, fn):
    t = time.time()
    try:
        r = fn()
        print(f"\n{label}: HTTP {r.status_code} in {time.time() - t:.1f}s")
        print(r.text[:300])
    except Exception as e:
        print(f"\n{label}: FAILED after {time.time() - t:.1f}s -> {e!r}")


print("Gemini model:", s.gemini_model)
timed("Gemini", lambda: httpx.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/{s.gemini_model}:generateContent",
    headers={"x-goog-api-key": s.gemini_api_key},
    json={"contents": [{"parts": [{"text": "Say hi in one word"}]}]}, timeout=40))

timed("Channel3", lambda: httpx.post(
    f"{s.channel3_base_url}/v1/search",
    headers={"x-api-key": s.channel3_api_key},
    json={"query": "phone", "limit": 3}, timeout=40))