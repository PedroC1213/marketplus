"""
MarketPlus - Agregador de Riesgo por Vendedor
Calcula el perfil de riesgo de un vendedor en base a sus reseñas analizadas.
Alimenta la vista SellersTable.jsx del frontend.
"""

from collections import defaultdict, Counter
from typing import List, Dict
import logging

from models.schemas import Review, FraudScore, SellerRiskProfile, RiskLevel

logger = logging.getLogger(__name__)


class SellerRiskAggregator:
    """
    Agrega los scores de reseñas individuales al nivel del vendedor.
    """

    RISK_THRESHOLDS = {
        RiskLevel.ALTO: 0.55,
        RiskLevel.MEDIO: 0.30,
    }

    def aggregate(
        self,
        reviews: List[Review],
        scores: List[FraudScore],
        seller_names: Dict[str, str] = None,
    ) -> List[SellerRiskProfile]:
        """
        Calcula el perfil de riesgo de cada vendedor.

        Args:
            reviews: Lista de reseñas (con seller_id).
            scores: Scores de fraude correspondientes.
            seller_names: Mapa opcional seller_id → nombre legible.

        Returns:
            Lista de SellerRiskProfile, ordenada por avg_risk_score desc.
        """
        seller_names = seller_names or {}
        score_map: Dict[int, FraudScore] = {s.review_id: s for s in scores}

        # Agrupar por vendedor
        by_seller: Dict[str, List[Review]] = defaultdict(list)
        for r in reviews:
            by_seller[r.seller_id].append(r)

        profiles: List[SellerRiskProfile] = []
        for seller_id, seller_reviews in by_seller.items():
            profile = self._build_profile(
                seller_id,
                seller_names.get(seller_id, seller_id),
                seller_reviews,
                score_map,
            )
            profiles.append(profile)

        # Ordenar por riesgo descendente (igual que el frontend)
        profiles.sort(key=lambda p: p.avg_risk_score, reverse=True)
        return profiles

    def _build_profile(
        self,
        seller_id: str,
        seller_name: str,
        reviews: List[Review],
        score_map: Dict[int, FraudScore],
    ) -> SellerRiskProfile:
        scored = [score_map[r.id] for r in reviews if r.id in score_map]
        flagged = [s for s in scored if s.risk_level != RiskLevel.BAJO]

        avg_score = (
            sum(s.score for s in scored) / len(scored) if scored else 0.0
        )

        # Top razones más frecuentes
        all_reasons = [reason for s in flagged for reason in s.reasons]
        top_reasons = [r for r, _ in Counter(all_reasons).most_common(3)]

        # Nivel de riesgo del vendedor
        risk_level = self._score_to_risk(avg_score)

        # Contar productos únicos
        products = len({r.product_id for r in reviews})

        return SellerRiskProfile(
            seller_id=seller_id,
            seller_name=seller_name,
            total_products=products,
            total_reviews=len(reviews),
            flagged_reviews=len(flagged),
            avg_risk_score=round(avg_score, 4),
            risk_level=risk_level,
            top_reasons=top_reasons,
        )

    def _score_to_risk(self, score: float) -> RiskLevel:
        if score >= self.RISK_THRESHOLDS[RiskLevel.ALTO]:
            return RiskLevel.ALTO
        elif score >= self.RISK_THRESHOLDS[RiskLevel.MEDIO]:
            return RiskLevel.MEDIO
        return RiskLevel.BAJO
