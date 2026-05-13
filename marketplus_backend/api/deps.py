"""
MarketPlus API — Dependencias compartidas (FastAPI Depends)
- Inyección de la conexión a BD
- Verificación de JWT para rutas protegidas
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.schema import create_tables

logger = logging.getLogger(__name__)

# ── Singleton de BD ───────────────────────────────────────────
_db: Optional[DatabaseConnection] = None

def startup_db() -> None:
    global _db
    config = DatabaseConfig.from_env()
    _db = DatabaseConnection(config)
    _db.connect()
    create_tables(_db)
    logger.info("Base de datos lista.")

def get_db() -> DatabaseConnection:
    if _db is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    return _db

# ── JWT mínimo (sin dependencia externa pesada) ───────────────
import json, hmac, hashlib, base64

SECRET_KEY = os.environ.get("JWT_SECRET", "marketplus-dev-secret-change-in-prod")
ALGORITHM  = "HS256"
TOKEN_TTL  = int(os.environ.get("JWT_TTL_HOURS", "24"))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (padding % 4))


def create_token(user_id: int, email: str) -> str:
    header  = _b64url_encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode())
    payload = _b64url_encode(json.dumps({
        "sub": str(user_id),
        "email": email,
        "exp": (datetime.utcnow() + timedelta(hours=TOKEN_TTL)).timestamp(),
    }).encode())
    sig = _b64url_encode(
        hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{sig}"


def verify_token(token: str) -> dict:
    try:
        header, payload, sig = token.split(".")
    except ValueError:
        raise HTTPException(status_code=401, detail="Token malformado")

    expected = _b64url_encode(
        hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="Firma inválida")

    data = json.loads(_b64url_decode(payload))
    if datetime.utcfromtimestamp(data["exp"]) < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expirado")
    return data


# ── Bearer security scheme ────────────────────────────────────
_bearer = HTTPBearer(auto_error=False)

def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """Dependencia que exige JWT válido. Inyectar en rutas protegidas."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Token requerido")
    return verify_token(credentials.credentials)
