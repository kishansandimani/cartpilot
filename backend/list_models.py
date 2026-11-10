"""Lists Gemini models your key can use and tests each one. Run:  python list_models.py"""
import time
import httpx
from app.config import get_settings

key = get_settings().gemini_api_key
r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models",
              headers={"x-goog-api-key": key}, params={"pageSize": 200}, timeout=30)
r.raise_for_status()
names = [m["name"].removeprefix("models/") for m in r.json().get("models", [])
         if "generateContent" in m.get("supportedGenerationMethods", [])
         and "flash" in m["name"] and not any(x in m["name"] for x in ("image", "tts", "audio", "live", "embedding", "thinking-exp"))]

print(f"Testing {len(names)} flash models...\n")
for n in names:
    t = time.time()
    try:
        x = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{n}:generateContent",
                       headers={"x-goog-api-key": key},
                       json={"contents": [{"parts": [{"text": "Say hi in one word"}]}]}, timeout=25)
        print(f"{'OK  ' if x.status_code == 200 else x.status_code}  {n}  ({time.time() - t:.1f}s)")
    except Exception as e:
        print(f"FAIL {n}  ({type(e).__name__})")