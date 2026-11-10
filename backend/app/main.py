from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db
from .routers import (analytics, auth, cart, chat, compare, external_orders, integrations, orders, payments,
                      products, recommendations, users, voice)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings().require_jwt_secret()  # fail early with a clear message
    init_db()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan,
              description="CartPilot AI - voice-first AI shopping assistant API. Interactive docs: /docs")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

for r in (auth, users, chat, voice, products, recommendations, compare, cart, payments, orders,
          external_orders, integrations, analytics):
    app.include_router(r.router)


@app.get("/api/health", tags=["health"])
def health():
    s = get_settings()
    return {"status": "ok", "gemini_configured": bool(s.gemini_api_key), "product_provider": s.product_provider,
            "product_provider_configured": s.product_provider == "fixtures" or bool(s.channel3_api_key),
            "paypal_configured": bool(s.paypal_client_id and s.paypal_client_secret), "paypal_env": s.paypal_env}


# Optional: serve the built React app from the same server (used on Render's single-service setup).
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = _dist / full_path
        return FileResponse(candidate if candidate.is_file() else _dist / "index.html")
