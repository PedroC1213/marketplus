"""
MarketPlus API — FastAPI
Punto de entrada del servidor. Registra todos los routers y configura CORS
para que el frontend Astro (puerto 4321) pueda consumir la API.

Arrancar:
    uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import reviews, campaigns, sellers, dashboard, auth
from api.deps import get_db, startup_db

app = FastAPI(
    title="MarketPlus ReviewGuard API",
    description="API de detección de fraude en reseñas con IA",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────
# Permite peticiones desde el frontend Astro en desarrollo y producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4321",   # astro dev
        "http://localhost:3000",
        "http://127.0.0.1:4321",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Ciclo de vida ─────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    startup_db()

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router,       prefix="/api/auth",      tags=["auth"])
app.include_router(reviews.router,    prefix="/api/reviews",   tags=["reviews"])
app.include_router(campaigns.router,  prefix="/api/campaigns", tags=["campaigns"])
app.include_router(sellers.router,    prefix="/api/sellers",   tags=["sellers"])
app.include_router(dashboard.router,  prefix="/api/dashboard", tags=["dashboard"])

@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok", "service": "ReviewGuard API"}
