"""
MarketPlus API — Router: Reviews
GET  /api/reviews              → lista filtrable por riesgo
GET  /api/reviews/{id}         → detalle con score, metadatos, campaña
POST /api/reviews/{id}/action  → aprobar | eliminar | marcar para revisión
POST /api/reviews/analyze      → analizar una reseña nueva con el modelo IA
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from api.schemas import ReviewOut, ReviewListResponse, ReviewAction
from api.deps import get_db, require_auth
from database.connection import DatabaseConnection
from database.repositories import ReviewRepository, FraudScoreRepository, CampaignRepository
from detector.fraud_detector import FraudDetector
from models.schemas import Review, ReviewMetadata, RiskLevel

router = APIRouter()
logger = logging.getLogger(__name__)

# Detector singleton (cargado una vez en memoria)
_detector = FraudDetector()


def _relative_time(dt: datetime) -> str:
    """Convierte datetime a string relativo para el frontend: 'Hace 2h', 'Ayer', etc."""
    if dt is None:
        return "—"
    delta = datetime.utcnow() - dt
    if delta.total_seconds() < 3600:
        mins = int(delta.total_seconds() / 60)
        return f"Hace {mins}m"
    elif delta.total_seconds() < 86400:
        hrs = int(delta.total_seconds() / 3600)
        return f"Hace {hrs}h"
    elif delta.days == 1:
        return "Ayer"
    return dt.strftime("%Y-%m-%d")


def _row_to_review_out(
    row: dict,
    score_row: Optional[dict],
    campaign_row: Optional[dict],
) -> ReviewOut:
    risk = score_row["risk_level"] if score_row else "Bajo"
    score_val = float(score_row["score"]) if score_row else None
    reasons = []
    if score_row and score_row.get("reasons"):
        import json
        reasons = json.loads(score_row["reasons"]) if isinstance(score_row["reasons"], str) else score_row["reasons"]

    campaign_str = None
    if campaign_row:
        campaign_str = f'Campaña #{campaign_row["id"]}: {campaign_row["description"][:60]}'

    # Metadatos formateados para ReviewDetail.jsx
    metadata = {
        "ip": row.get("ip", "—"),
        "device": row.get("device", "—"),
        "date": row["review_date"].strftime("%Y-%m-%d %H:%M:%S") if row.get("review_date") else "—",
        "user_id": row.get("user_id", "—"),
        "previous_reviews": row.get("previous_reviews", 0),
    }

    return ReviewOut(
        id=row["id"],
        product=row.get("product_name") or row.get("product_id", "—"),
        rating=row["rating"],
        text=row["text"],
        risk=risk,
        score=score_val,
        date=row["review_date"].strftime("%Y-%m-%d") if row.get("review_date") else "—",
        user=row.get("user_id", "—"),
        reasons=reasons,
        metadata=metadata,
        campaign=campaign_str,
    )


# ── GET /api/reviews ──────────────────────────────────────────

@router.get("", response_model=ReviewListResponse)
def list_reviews(
    risk: Optional[str] = Query(None, description="Bajo | Medio | Alto"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: DatabaseConnection = Depends(get_db),
    _user: dict = Depends(require_auth),
):
    """
    Devuelve reseñas con sus scores de riesgo.
    Equivale a los mockReviews de ReviewsTable.jsx.
    """
    # Query base con JOIN a productos para obtener el nombre
    base_sql = """
        SELECT r.*, p.name AS product_name
        FROM reviews r
        LEFT JOIN products p ON p.id = r.product_id
        LEFT JOIN fraud_scores fs ON fs.review_id = r.id
        {where}
        ORDER BY r.review_date DESC
        LIMIT %s OFFSET %s
    """
    count_sql = """
        SELECT COUNT(*) AS cnt
        FROM reviews r
        LEFT JOIN fraud_scores fs ON fs.review_id = r.id
        {where}
    """

    if risk and risk != "Todos":
        where = "WHERE fs.risk_level = %s"
        params_rows  = (risk, limit, offset)
        params_count = (risk,)
    else:
        where = ""
        params_rows  = (limit, offset)
        params_count = ()

    rows  = db.execute(base_sql.format(where=where), params_rows)
    total = db.execute(count_sql.format(where=where), params_count)[0]["cnt"]

    # Cargar scores y campañas en batch
    review_ids = [r["id"] for r in rows]
    scores_map: dict = {}
    campaigns_map: dict = {}

    if review_ids:
        placeholders = ",".join(["%s"] * len(review_ids))
        score_rows = db.execute(
            f"SELECT * FROM fraud_scores WHERE review_id IN ({placeholders})",
            tuple(review_ids),
        )
        scores_map = {s["review_id"]: s for s in score_rows}

        # Campañas: buscar en review_ids JSON (simplificado)
        camp_rows = db.execute(
            "SELECT id, description, review_ids FROM fraud_campaigns WHERE status != 'cerrada'"
        )
        import json
        for camp in camp_rows:
            ids = json.loads(camp["review_ids"]) if isinstance(camp["review_ids"], str) else camp["review_ids"]
            for rid in ids:
                if rid in review_ids:
                    campaigns_map[rid] = camp

    result = [
        _row_to_review_out(row, scores_map.get(row["id"]), campaigns_map.get(row["id"]))
        for row in rows
    ]
    return ReviewListResponse(reviews=result, total=total)


# ── GET /api/reviews/{id} ─────────────────────────────────────

@router.get("/{review_id}", response_model=ReviewOut)
def get_review(
    review_id: int,
    db: DatabaseConnection = Depends(get_db),
    _user: dict = Depends(require_auth),
):
    rows = db.execute(
        """
        SELECT r.*, p.name AS product_name
        FROM reviews r
        LEFT JOIN products p ON p.id = r.product_id
        WHERE r.id = %s LIMIT 1
        """,
        (review_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    score_rows = db.execute(
        "SELECT * FROM fraud_scores WHERE review_id = %s LIMIT 1", (review_id,)
    )
    score_row = score_rows[0] if score_rows else None

    # Buscar campaña asociada
    import json
    camp_rows = db.execute(
        "SELECT id, description, review_ids FROM fraud_campaigns"
    )
    campaign_row = None
    for camp in camp_rows:
        ids = json.loads(camp["review_ids"]) if isinstance(camp["review_ids"], str) else camp["review_ids"]
        if review_id in ids:
            campaign_row = camp
            break

    return _row_to_review_out(rows[0], score_row, campaign_row)


# ── POST /api/reviews/{id}/action ────────────────────────────

@router.post("/{review_id}/action")
def review_action(
    review_id: int,
    body: ReviewAction,
    db: DatabaseConnection = Depends(get_db),
    _user: dict = Depends(require_auth),
):
    """
    Acciones de moderación: approve | delete | flag
    Equivale a los botones de ReviewDetail.jsx
    """
    rows = db.execute("SELECT id FROM reviews WHERE id = %s LIMIT 1", (review_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    if body.action == "delete":
        db.execute_write("DELETE FROM reviews WHERE id = %s", (review_id,))
        return {"ok": True, "message": "Reseña eliminada"}

    elif body.action == "approve":
        # Actualizar score a Bajo para marcarla como aprobada
        db.execute_write(
            """
            INSERT INTO fraud_scores (review_id, risk_level, score, reasons)
            VALUES (%s, 'Bajo', 0.0, '["Aprobada manualmente"]')
            ON DUPLICATE KEY UPDATE risk_level='Bajo', score=0.0, reasons='["Aprobada manualmente"]'
            """,
            (review_id,),
        )
        return {"ok": True, "message": "Reseña aprobada"}

    elif body.action == "flag":
        db.execute_write(
            """
            INSERT INTO fraud_scores (review_id, risk_level, score, reasons)
            VALUES (%s, 'Medio', 0.5, '["Marcada para revisión manual"]')
            ON DUPLICATE KEY UPDATE risk_level='Medio', score=0.5, reasons='["Marcada para revisión manual"]'
            """,
            (review_id,),
        )
        return {"ok": True, "message": "Reseña marcada para revisión"}

    raise HTTPException(status_code=400, detail=f"Acción desconocida: {body.action}")


# ── POST /api/reviews/analyze ─────────────────────────────────

@router.post("/analyze")
def analyze_review(
    body: dict,
    db: DatabaseConnection = Depends(get_db),
    _user: dict = Depends(require_auth),
):
    """
    Analiza una reseña en tiempo real con el modelo IA y la guarda en BD.
    Body: { product_id, seller_id, rating, text, user_id, ip, device }
    """
    from database.repositories import ReviewRepository, FraudScoreRepository

    # Construir objeto Review
    meta = ReviewMetadata(
        ip=body.get("ip", "0.0.0.0"),
        device=body.get("device", "unknown"),
        user_id=body.get("user_id", "unknown"),
        date=datetime.utcnow(),
        previous_reviews=body.get("previous_reviews", 0),
        account_age_days=body.get("account_age_days", 0),
    )
    review = Review(
        id=0,
        product=body.get("product_id", ""),
        product_id=body.get("product_id", ""),
        seller_id=body.get("seller_id", ""),
        rating=body.get("rating", 3),
        text=body.get("text", ""),
        user=body.get("user_id", "unknown"),
        metadata=meta,
    )

    # Obtener contexto reciente para el análisis
    review_repo = ReviewRepository(db)
    score_repo  = FraudScoreRepository(db)

    context = review_repo.get_recent_by_product(review.product_id, minutes=60, limit=100)

    # Insertar la reseña
    review_id = review_repo.insert(review)
    review.id = review_id

    # Analizar con el modelo
    fraud_score = _detector.analyze(review, context)
    fraud_score.review_id = review_id
    score_repo.upsert(fraud_score)

    return {
        "review_id": review_id,
        "risk_level": fraud_score.risk_level.value,
        "score": fraud_score.score,
        "reasons": fraud_score.reasons,
    }
