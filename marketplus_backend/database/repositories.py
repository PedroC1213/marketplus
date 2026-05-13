"""
MarketPlus - Repositorios de Base de Datos
Una clase por entidad con métodos CRUD alineados a los schemas del dominio.
Cada repositorio recibe un DatabaseConnection ya inicializado.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from database.connection import DatabaseConnection
from models.schemas import (
    Review, ReviewMetadata, FraudScore, FraudCampaign,
    SellerRiskProfile, Alert, RiskLevel,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Helpers de conversión
# ──────────────────────────────────────────────────────────────

def _to_datetime(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _parse_json_field(value) -> list:
    """Parsea un campo JSON que puede venir como str o como list/dict."""
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    return json.loads(value)


# ──────────────────────────────────────────────────────────────
# ReviewRepository
# ──────────────────────────────────────────────────────────────

class ReviewRepository:
    """
    Lee y escribe reseñas en la tabla `reviews`.
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # ── Lectura ────────────────────────────────────────────────

    def get_by_id(self, review_id: int) -> Optional[Review]:
        rows = self.db.execute(
            "SELECT * FROM reviews WHERE id = %s LIMIT 1",
            (review_id,)
        )
        return self._row_to_review(rows[0]) if rows else None

    def get_recent_by_product(
        self,
        product_id: str,
        minutes: int = 60,
        limit: int = 200,
    ) -> List[Review]:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        rows = self.db.execute(
            """
            SELECT * FROM reviews
            WHERE product_id = %s AND review_date >= %s
            ORDER BY review_date DESC
            LIMIT %s
            """,
            (product_id, cutoff, limit),
        )
        return [self._row_to_review(r) for r in rows]

    def get_recent_by_seller(
        self,
        seller_id: str,
        minutes: int = 1440,   # 24 h por defecto
        limit: int = 500,
    ) -> List[Review]:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        rows = self.db.execute(
            """
            SELECT * FROM reviews
            WHERE seller_id = %s AND review_date >= %s
            ORDER BY review_date DESC
            LIMIT %s
            """,
            (seller_id, cutoff, limit),
        )
        return [self._row_to_review(r) for r in rows]

    def get_unscored(self, limit: int = 100) -> List[Review]:
        """Reseñas que aún no tienen fraud_score asociado."""
        rows = self.db.execute(
            """
            SELECT r.* FROM reviews r
            LEFT JOIN fraud_scores fs ON fs.review_id = r.id
            WHERE fs.id IS NULL
            ORDER BY r.review_date ASC
            LIMIT %s
            """,
            (limit,),
        )
        return [self._row_to_review(r) for r in rows]

    def count_by_ip_in_window(self, ip: str, product_id: str, minutes: int = 60) -> int:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        rows = self.db.execute(
            """
            SELECT COUNT(*) AS cnt FROM reviews
            WHERE ip = %s AND product_id = %s AND review_date >= %s
            """,
            (ip, product_id, cutoff),
        )
        return rows[0]["cnt"] if rows else 0

    # ── Escritura ──────────────────────────────────────────────

    def insert(self, review: Review) -> int:
        """Inserta una reseña y devuelve el ID generado."""
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reviews
                    (product_id, seller_id, user_id, rating, text,
                     ip, device, previous_reviews, account_age_days, review_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    review.product_id,
                    review.seller_id,
                    review.metadata.user_id,
                    review.rating,
                    review.text,
                    review.metadata.ip,
                    review.metadata.device,
                    review.metadata.previous_reviews,
                    review.metadata.account_age_days,
                    review.date or datetime.utcnow(),
                ),
            )
            return cur.lastrowid

    def insert_batch(self, reviews: List[Review]) -> int:
        """Inserta múltiples reseñas en un solo batch. Devuelve filas afectadas."""
        params = [
            (
                r.product_id, r.seller_id, r.metadata.user_id,
                r.rating, r.text, r.metadata.ip, r.metadata.device,
                r.metadata.previous_reviews, r.metadata.account_age_days,
                r.date or datetime.utcnow(),
            )
            for r in reviews
        ]
        return self.db.execute_many(
            """
            INSERT INTO reviews
                (product_id, seller_id, user_id, rating, text,
                 ip, device, previous_reviews, account_age_days, review_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params,
        )

    # ── Conversión ─────────────────────────────────────────────

    @staticmethod
    def _row_to_review(row: dict) -> Review:
        meta = ReviewMetadata(
            ip=row["ip"],
            device=row["device"],
            user_id=row["user_id"],
            date=_to_datetime(row.get("review_date")),
            previous_reviews=row.get("previous_reviews", 0),
            account_age_days=row.get("account_age_days", 0),
        )
        return Review(
            id=row["id"],
            product=row.get("product_name", row["product_id"]),
            product_id=row["product_id"],
            seller_id=row["seller_id"],
            rating=row["rating"],
            text=row["text"],
            user=row["user_id"],
            metadata=meta,
            date=_to_datetime(row.get("review_date")),
        )


# ──────────────────────────────────────────────────────────────
# FraudScoreRepository
# ──────────────────────────────────────────────────────────────

class FraudScoreRepository:
    """
    Lee y escribe resultados de análisis en `fraud_scores`.
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def get_by_review(self, review_id: int) -> Optional[FraudScore]:
        rows = self.db.execute(
            "SELECT * FROM fraud_scores WHERE review_id = %s LIMIT 1",
            (review_id,)
        )
        return self._row_to_score(rows[0]) if rows else None

    def get_high_risk(self, limit: int = 50) -> List[FraudScore]:
        rows = self.db.execute(
            """
            SELECT * FROM fraud_scores
            WHERE risk_level = 'Alto'
            ORDER BY score DESC, analyzed_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [self._row_to_score(r) for r in rows]

    def get_by_risk_level(self, risk_level: RiskLevel, limit: int = 100) -> List[FraudScore]:
        rows = self.db.execute(
            """
            SELECT * FROM fraud_scores
            WHERE risk_level = %s
            ORDER BY analyzed_at DESC
            LIMIT %s
            """,
            (risk_level.value, limit),
        )
        return [self._row_to_score(r) for r in rows]

    def upsert(self, score: FraudScore) -> None:
        """Inserta o actualiza el score de una reseña (ON DUPLICATE KEY)."""
        self.db.execute_write(
            """
            INSERT INTO fraud_scores (review_id, risk_level, score, reasons, campaign_id, analyzed_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                risk_level  = VALUES(risk_level),
                score       = VALUES(score),
                reasons     = VALUES(reasons),
                campaign_id = VALUES(campaign_id),
                analyzed_at = VALUES(analyzed_at)
            """,
            (
                score.review_id,
                score.risk_level.value,
                score.score,
                json.dumps(score.reasons, ensure_ascii=False),
                score.campaign_id,
                score.analyzed_at or datetime.utcnow(),
            ),
        )

    def upsert_batch(self, scores: List[FraudScore]) -> int:
        params = [
            (
                s.review_id,
                s.risk_level.value,
                s.score,
                json.dumps(s.reasons, ensure_ascii=False),
                s.campaign_id,
                s.analyzed_at or datetime.utcnow(),
            )
            for s in scores
        ]
        return self.db.execute_many(
            """
            INSERT INTO fraud_scores (review_id, risk_level, score, reasons, campaign_id, analyzed_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                risk_level  = VALUES(risk_level),
                score       = VALUES(score),
                reasons     = VALUES(reasons),
                campaign_id = VALUES(campaign_id),
                analyzed_at = VALUES(analyzed_at)
            """,
            params,
        )

    @staticmethod
    def _row_to_score(row: dict) -> FraudScore:
        return FraudScore(
            review_id=row["review_id"],
            risk_level=RiskLevel(row["risk_level"]),
            score=float(row["score"]),
            reasons=_parse_json_field(row.get("reasons")),
            campaign_id=row.get("campaign_id"),
            analyzed_at=_to_datetime(row.get("analyzed_at")),
        )


# ──────────────────────────────────────────────────────────────
# CampaignRepository
# ──────────────────────────────────────────────────────────────

class CampaignRepository:
    """
    Lee y escribe campañas de fraude detectadas en `fraud_campaigns`.
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def get_active(self, limit: int = 50) -> List[FraudCampaign]:
        rows = self.db.execute(
            """
            SELECT * FROM fraud_campaigns
            WHERE status = 'activa'
            ORDER BY detected_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [self._row_to_campaign(r) for r in rows]

    def get_by_seller(self, seller_id: str) -> List[FraudCampaign]:
        rows = self.db.execute(
            "SELECT * FROM fraud_campaigns WHERE seller_id = %s ORDER BY detected_at DESC",
            (seller_id,),
        )
        return [self._row_to_campaign(r) for r in rows]

    def insert(self, campaign: FraudCampaign) -> int:
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fraud_campaigns
                    (description, severity, seller_id, review_ids, status, detected_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    campaign.description,
                    campaign.severity.value,
                    campaign.seller_id,
                    json.dumps(campaign.review_ids),
                    campaign.status,
                    campaign.detected_at or datetime.utcnow(),
                ),
            )
            return cur.lastrowid

    def insert_batch(self, campaigns: List[FraudCampaign]) -> int:
        params = [
            (
                c.description,
                c.severity.value,
                c.seller_id,
                json.dumps(c.review_ids),
                c.status,
                c.detected_at or datetime.utcnow(),
            )
            for c in campaigns
        ]
        return self.db.execute_many(
            """
            INSERT INTO fraud_campaigns
                (description, severity, seller_id, review_ids, status, detected_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            params,
        )

    def update_status(self, campaign_id: int, status: str) -> None:
        self.db.execute_write(
            "UPDATE fraud_campaigns SET status = %s WHERE id = %s",
            (status, campaign_id),
        )

    @staticmethod
    def _row_to_campaign(row: dict) -> FraudCampaign:
        return FraudCampaign(
            campaign_id=row["id"],
            description=row["description"],
            review_ids=_parse_json_field(row.get("review_ids")),
            severity=RiskLevel(row["severity"]),
            seller_id=row.get("seller_id"),
            detected_at=_to_datetime(row.get("detected_at")),
            status=row.get("status", "activa"),
        )


# ──────────────────────────────────────────────────────────────
# SellerProfileRepository
# ──────────────────────────────────────────────────────────────

class SellerProfileRepository:
    """
    Lee y escribe perfiles de riesgo de vendedores en `seller_risk_profiles`.
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def get_all(self, order_by: str = "avg_risk_score") -> List[SellerRiskProfile]:
        allowed = {"avg_risk_score", "flagged_reviews", "total_reviews"}
        col = order_by if order_by in allowed else "avg_risk_score"
        rows = self.db.execute(
            f"SELECT * FROM seller_risk_profiles ORDER BY {col} DESC"
        )
        return [self._row_to_profile(r) for r in rows]

    def get_by_seller(self, seller_id: str) -> Optional[SellerRiskProfile]:
        rows = self.db.execute(
            "SELECT * FROM seller_risk_profiles WHERE seller_id = %s LIMIT 1",
            (seller_id,),
        )
        return self._row_to_profile(rows[0]) if rows else None

    def upsert(self, profile: SellerRiskProfile) -> None:
        self.db.execute_write(
            """
            INSERT INTO seller_risk_profiles
                (seller_id, seller_name, total_products, total_reviews,
                 flagged_reviews, avg_risk_score, risk_level, top_reasons)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                seller_name     = VALUES(seller_name),
                total_products  = VALUES(total_products),
                total_reviews   = VALUES(total_reviews),
                flagged_reviews = VALUES(flagged_reviews),
                avg_risk_score  = VALUES(avg_risk_score),
                risk_level      = VALUES(risk_level),
                top_reasons     = VALUES(top_reasons)
            """,
            (
                profile.seller_id,
                profile.seller_name,
                profile.total_products,
                profile.total_reviews,
                profile.flagged_reviews,
                profile.avg_risk_score,
                profile.risk_level.value,
                json.dumps(profile.top_reasons, ensure_ascii=False),
            ),
        )

    def upsert_batch(self, profiles: List[SellerRiskProfile]) -> int:
        params = [
            (
                p.seller_id, p.seller_name, p.total_products,
                p.total_reviews, p.flagged_reviews, p.avg_risk_score,
                p.risk_level.value,
                json.dumps(p.top_reasons, ensure_ascii=False),
            )
            for p in profiles
        ]
        return self.db.execute_many(
            """
            INSERT INTO seller_risk_profiles
                (seller_id, seller_name, total_products, total_reviews,
                 flagged_reviews, avg_risk_score, risk_level, top_reasons)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                seller_name     = VALUES(seller_name),
                total_products  = VALUES(total_products),
                total_reviews   = VALUES(total_reviews),
                flagged_reviews = VALUES(flagged_reviews),
                avg_risk_score  = VALUES(avg_risk_score),
                risk_level      = VALUES(risk_level),
                top_reasons     = VALUES(top_reasons)
            """,
            params,
        )

    @staticmethod
    def _row_to_profile(row: dict) -> SellerRiskProfile:
        return SellerRiskProfile(
            seller_id=row["seller_id"],
            seller_name=row["seller_name"],
            total_products=row["total_products"],
            total_reviews=row["total_reviews"],
            flagged_reviews=row["flagged_reviews"],
            avg_risk_score=float(row["avg_risk_score"]),
            risk_level=RiskLevel(row["risk_level"]),
            top_reasons=_parse_json_field(row.get("top_reasons")),
        )


# ──────────────────────────────────────────────────────────────
# AlertRepository
# ──────────────────────────────────────────────────────────────

class AlertRepository:
    """
    Escribe y lee alertas activas en `alerts`.
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def get_recent(self, limit: int = 20) -> List[dict]:
        return self.db.execute(
            """
            SELECT * FROM alerts
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )

    def get_high_risk(self, limit: int = 10) -> List[dict]:
        return self.db.execute(
            """
            SELECT * FROM alerts
            WHERE risk = 'Alto'
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )

    def insert(self, alert: Alert) -> int:
        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alerts (product_id, product_name, risk, reason, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    alert.product_id,
                    alert.product,
                    alert.risk.value,
                    alert.reason,
                    alert.time or datetime.utcnow(),
                ),
            )
            return cur.lastrowid

    def insert_from_scores(
        self,
        reviews: List[Review],
        scores: List[FraudScore],
    ) -> int:
        """Genera alertas automáticamente a partir de scores de alto riesgo."""
        score_map = {s.review_id: s for s in scores}
        alerts_to_insert = []
        for review in reviews:
            score = score_map.get(review.id)
            if score and score.risk_level == RiskLevel.ALTO:
                reason = score.reasons[0] if score.reasons else "Riesgo alto detectado"
                alerts_to_insert.append((
                    review.product_id,
                    review.product,
                    RiskLevel.ALTO.value,
                    reason,
                    datetime.utcnow(),
                ))

        if not alerts_to_insert:
            return 0

        return self.db.execute_many(
            """
            INSERT INTO alerts (product_id, product_name, risk, reason, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            alerts_to_insert,
        )
