"""
MarketPlus API — Router: Auth
POST /api/auth/login
POST /api/auth/register
"""

import hashlib
import logging
from fastapi import APIRouter, Depends, HTTPException

from api.schemas import LoginRequest, RegisterRequest, AuthResponse
from api.deps import get_db, create_token
from database.connection import DatabaseConnection

router = APIRouter()
logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Tabla de usuarios (se crea si no existe) ──────────────────
_USERS_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id          INT             NOT NULL AUTO_INCREMENT,
    email       VARCHAR(255)    NOT NULL,
    password    VARCHAR(64)     NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

_DEFAULT_USER_SQL = """
INSERT IGNORE INTO users (email, password)
VALUES ('admin@marketplus.com', %s)
"""


def _ensure_users_table(db: DatabaseConnection) -> None:
    with db.cursor() as cur:
        cur.execute(_USERS_DDL)
    # Insertar usuario demo si no existe
    db.execute_write(_DEFAULT_USER_SQL, (_hash_password("123456"),))


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: DatabaseConnection = Depends(get_db)):
    _ensure_users_table(db)
    rows = db.execute(
        "SELECT id, email FROM users WHERE email = %s AND password = %s LIMIT 1",
        (body.email, _hash_password(body.password)),
    )
    if not rows:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    user = rows[0]
    token = create_token(user["id"], user["email"])
    return AuthResponse(
        token=token,
        user={"id": user["id"], "email": user["email"]},
    )


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: DatabaseConnection = Depends(get_db)):
    _ensure_users_table(db)

    existing = db.execute(
        "SELECT id FROM users WHERE email = %s LIMIT 1",
        (body.email,),
    )
    if existing:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (body.email, _hash_password(body.password)),
        )
        user_id = cur.lastrowid

    token = create_token(user_id, body.email)
    return AuthResponse(
        token=token,
        user={"id": user_id, "email": body.email},
    )
