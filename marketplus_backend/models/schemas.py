"""
MarketPlus - Esquemas de datos
Define las estructuras de datos usadas en todo el sistema de detección de fraude.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    """Niveles de riesgo alineados con el frontend."""
    BAJO = "Bajo"
    MEDIO = "Medio"
    ALTO = "Alto"


@dataclass
class ReviewMetadata:
    """Metadatos asociados a una reseña (dispositivo, IP, historial)."""
    ip: str
    device: str
    user_id: str
    date: datetime
    previous_reviews: int = 0
    account_age_days: int = 0


@dataclass
class Review:
    """Reseña de producto tal como llega al sistema."""
    id: int
    product: str
    product_id: str
    seller_id: str
    rating: int                    # 1–5
    text: str
    user: str
    metadata: ReviewMetadata
    date: Optional[datetime] = None

    def __post_init__(self):
        if self.date is None:
            self.date = datetime.utcnow()


@dataclass
class FraudScore:
    """Resultado del análisis de una reseña individual."""
    review_id: int
    risk_level: RiskLevel
    score: float                   # 0.0 – 1.0
    reasons: List[str] = field(default_factory=list)
    campaign_id: Optional[int] = None
    analyzed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SellerRiskProfile:
    """Perfil de riesgo agregado de un vendedor."""
    seller_id: str
    seller_name: str
    total_products: int
    total_reviews: int
    flagged_reviews: int
    avg_risk_score: float          # 0.0 – 1.0
    risk_level: RiskLevel
    top_reasons: List[str] = field(default_factory=list)


@dataclass
class FraudCampaign:
    """Campaña de fraude detectada (grupo de reseñas coordinadas)."""
    campaign_id: int
    description: str
    review_ids: List[int]
    severity: RiskLevel
    seller_id: Optional[str]
    detected_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "activa"         # activa | en revisión | cerrada


@dataclass
class Alert:
    """Alerta generada por el sistema."""
    id: int
    product: str
    product_id: str
    risk: RiskLevel
    reason: str
    time: datetime = field(default_factory=datetime.utcnow)
