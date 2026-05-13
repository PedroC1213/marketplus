"""
MarketPlus API — Schemas Pydantic
Todos los modelos de request y response que consumen los routers.
Alineados exactamente con los tipos TypeScript del frontend (src/types/index.ts).
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    token: str
    user: dict


# ── Review ────────────────────────────────────────────────────
# Alineado con interface Review en types/index.ts

class ReviewOut(BaseModel):
    id: int
    product: str
    rating: int
    text: str
    risk: str                  # 'Bajo' | 'Medio' | 'Alto'
    score: Optional[float]
    date: str
    user: str
    reasons: List[str] = []
    metadata: Optional[dict] = None
    campaign: Optional[str] = None

class ReviewListResponse(BaseModel):
    reviews: List[ReviewOut]
    total: int

class ReviewAction(BaseModel):
    action: str                # 'approve' | 'delete' | 'flag'


# ── Alert ─────────────────────────────────────────────────────
# Alineado con interface Alert en types/index.ts

class AlertOut(BaseModel):
    id: int
    product: str
    risk: str                  # 'Bajo' | 'Medio' | 'Alto'
    reason: str
    time: str                  # string relativo para el frontend ("Hace 2h")


# ── Campaign ──────────────────────────────────────────────────
# Alineado con interface Campaign en types/index.ts

class CampaignOut(BaseModel):
    id: int
    name: str                  # descripción corta (frontend usa "name")
    description: str
    status: str                # 'activa' | 'en revisión' | 'cerrada' → mapeado a Activa/Pausada/Completada
    reviews: int               # reviewsCount
    riskLevel: str             # 'Bajo' | 'Medio' | 'Alto'
    date: str
    seller_id: Optional[str] = None

class CampaignListResponse(BaseModel):
    campaigns: List[CampaignOut]

class CampaignStatusUpdate(BaseModel):
    status: str                # 'activa' | 'en revisión' | 'cerrada'


# ── Seller ────────────────────────────────────────────────────
# Alineado con interface Seller en types/index.ts

class SellerOut(BaseModel):
    id: str
    name: str
    rating: float              # avg_risk_score (0-1), el frontend lo muestra como "rating"
    reviews: int               # total_reviews
    risk: str                  # 'Bajo' | 'Medio' | 'Alto'
    products: int
    flaggedReviews: int

class SellerListResponse(BaseModel):
    sellers: List[SellerOut]


# ── Dashboard ─────────────────────────────────────────────────

class RiskDistribution(BaseModel):
    bajo: int
    medio: int
    alto: int

class TrendPoint(BaseModel):
    date: str
    fraud: int

class DashboardStats(BaseModel):
    total_reviews: int
    flagged_today: int
    active_campaigns: int
    high_risk_sellers: int
    risk_distribution: RiskDistribution
    trend: List[TrendPoint]
    alerts: List[AlertOut]
