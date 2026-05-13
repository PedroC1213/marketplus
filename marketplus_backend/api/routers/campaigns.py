"""
MarketPlus API — Router: Campaigns
GET   /api/campaigns           → lista (alineada con CampaignsList.jsx)
PATCH /api/campaigns/{id}      → actualizar estado
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException

from api.schemas import CampaignOut, CampaignListResponse, CampaignStatusUpdate
from api.deps import get_db, require_auth
from database.connection import DatabaseConnection

router = APIRouter()
logger = logging.getLogger(__name__)

# Mapeo de status interno → label del frontend
_STATUS_LABEL = {
    "activa":       "Activa",
    "en revisión":  "Pausada",
    "cerrada":      "Completada",
}

# Mapeo de severidad → riskLevel frontend
_RISK_LABEL = {
    "Alto":  "Alto",
    "Medio": "Medio",
    "Bajo":  "Bajo",
    # aliases que pueden venir de la BD
    "Alta":  "Alto",
    "Media": "Medio",
    "Baja":  "Bajo",
}


@router.get("", response_model=CampaignListResponse)
def list_campaigns(
    db: DatabaseConnection = Depends(get_db),
    _user: dict = Depends(require_auth),
):
    """
    Devuelve todas las campañas activas y en revisión.
    Alimenta directamente a CampaignsList.jsx.
    """
    rows = db.execute(
        """
        SELECT id, description, severity, seller_id, review_ids, status,
               detected_at
        FROM fraud_campaigns
        WHERE status != 'cerrada'
        ORDER BY detected_at DESC
        LIMIT 100
        """
    )

    campaigns = []
    for row in rows:
        review_ids = json.loads(row["review_ids"]) if isinstance(row["review_ids"], str) else row["review_ids"]
        campaigns.append(CampaignOut(
            id=row["id"],
            name=f'Campaña #{row["id"]}',
            description=row["description"],
            status=_STATUS_LABEL.get(row["status"], row["status"]),
            reviews=len(review_ids),
            riskLevel=_RISK_LABEL.get(row["severity"], row["severity"]),
            date=row["detected_at"].strftime("%Y-%m-%d") if row.get("detected_at") else "—",
            seller_id=row.get("seller_id"),
        ))

    return CampaignListResponse(campaigns=campaigns)


@router.patch("/{campaign_id}")
def update_campaign_status(
    campaign_id: int,
    body: CampaignStatusUpdate,
    db: DatabaseConnection = Depends(get_db),
    _user: dict = Depends(require_auth),
):
    """
    Actualiza el estado de una campaña.
    Equivale al botón 'Marcar como revisada' de CampaignsList.jsx.
    """
    allowed = {"activa", "en revisión", "cerrada"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Opciones: {allowed}")

    rows = db.execute(
        "SELECT id FROM fraud_campaigns WHERE id = %s LIMIT 1", (campaign_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")

    db.execute_write(
        "UPDATE fraud_campaigns SET status = %s WHERE id = %s",
        (body.status, campaign_id),
    )
    return {"ok": True, "campaign_id": campaign_id, "status": body.status}
