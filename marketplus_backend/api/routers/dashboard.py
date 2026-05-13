"""
MarketPlus API — Router: Dashboard
GET /api/dashboard/stats   → KPIs, distribución de riesgo, tendencia semanal, alertas
                             Alimenta RiskChart.jsx, TrendChart.jsx y AlertsWidget.jsx
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends

from api.schemas import DashboardStats, RiskDistribution, TrendPoint, AlertOut
from api.deps import get_db, require_auth
from database.connection import DatabaseConnection

router = APIRouter()
logger = logging.getLogger(__name__)


def _relative_time(dt: datetime) -> str:
    if dt is None:
        return "—"
    delta = datetime.utcnow() - dt
    if delta.total_seconds() < 3600:
        mins = max(1, int(delta.total_seconds() / 60))
        return f"Hace {mins}m"
    elif delta.total_seconds() < 86400:
        hrs = int(delta.total_seconds() / 3600)
        return f"Hace {hrs}h"
    elif delta.days == 1:
        return "Ayer"
    return dt.strftime("%d/%m/%Y")


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    db: DatabaseConnection = Depends(get_db),
    _user: dict = Depends(require_auth),
):
    """
    Endpoint único que provee todos los datos que necesita la página /dashboard.
    Los componentes RiskChart, TrendChart y AlertsWidget consumen este endpoint.
    """

    # ── KPIs básicos ──────────────────────────────────────────
    total_reviews_row = db.execute("SELECT COUNT(*) AS cnt FROM reviews")
    total_reviews = total_reviews_row[0]["cnt"] if total_reviews_row else 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    flagged_today_row = db.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM fraud_scores fs
        JOIN reviews r ON r.id = fs.review_id
        WHERE fs.risk_level = 'Alto' AND r.review_date >= %s
        """,
        (today_start,),
    )
    flagged_today = flagged_today_row[0]["cnt"] if flagged_today_row else 0

    active_campaigns_row = db.execute(
        "SELECT COUNT(*) AS cnt FROM fraud_campaigns WHERE status = 'activa'"
    )
    active_campaigns = active_campaigns_row[0]["cnt"] if active_campaigns_row else 0

    high_risk_sellers_row = db.execute(
        "SELECT COUNT(*) AS cnt FROM seller_risk_profiles WHERE risk_level = 'Alto'"
    )
    high_risk_sellers = high_risk_sellers_row[0]["cnt"] if high_risk_sellers_row else 0

    # ── Distribución de riesgo (para RiskChart.jsx) ───────────
    risk_rows = db.execute(
        """
        SELECT risk_level, COUNT(*) AS cnt
        FROM fraud_scores
        GROUP BY risk_level
        """
    )
    risk_dist = {"Bajo": 0, "Medio": 0, "Alto": 0}
    for row in risk_rows:
        if row["risk_level"] in risk_dist:
            risk_dist[row["risk_level"]] = row["cnt"]

    # ── Tendencia semanal (para TrendChart.jsx) ───────────────
    trend: list[TrendPoint] = []
    DAY_NAMES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    for days_ago in range(6, -1, -1):
        day_start = (datetime.utcnow() - timedelta(days=days_ago)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        rows = db.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM fraud_scores fs
            JOIN reviews r ON r.id = fs.review_id
            WHERE fs.risk_level = 'Alto'
              AND r.review_date >= %s AND r.review_date < %s
            """,
            (day_start, day_end),
        )
        count = rows[0]["cnt"] if rows else 0
        weekday = day_start.weekday()   # 0=Lun … 6=Dom
        trend.append(TrendPoint(date=DAY_NAMES[weekday], fraud=count))

    # ── Alertas activas (para AlertsWidget.jsx) ───────────────
    alert_rows = db.execute(
        """
        SELECT id, product_name, risk, reason, created_at
        FROM alerts
        ORDER BY created_at DESC
        LIMIT 5
        """
    )
    alerts = [
        AlertOut(
            id=row["id"],
            product=row["product_name"],
            risk=row["risk"],
            reason=row["reason"],
            time=_relative_time(row["created_at"]),
        )
        for row in alert_rows
    ]

    return DashboardStats(
        total_reviews=total_reviews,
        flagged_today=flagged_today,
        active_campaigns=active_campaigns,
        high_risk_sellers=high_risk_sellers,
        risk_distribution=RiskDistribution(
            bajo=risk_dist["Bajo"],
            medio=risk_dist["Medio"],
            alto=risk_dist["Alto"],
        ),
        trend=trend,
        alerts=alerts,
    )
