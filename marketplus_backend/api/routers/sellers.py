"""
MarketPlus API — Router: Sellers
GET /api/sellers        → lista ordenable (alineada con SellersTable.jsx)
GET /api/sellers/{id}   → detalle de un vendedor
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query

from api.schemas import SellerOut, SellerListResponse
from api.deps import get_db, require_auth
from database.connection import DatabaseConnection

router = APIRouter()
logger = logging.getLogger(__name__)

_SORT_COLS = {
    "avgRisk":        "avg_risk_score",
    "flaggedReviews": "flagged_reviews",
    "reviews":        "total_reviews",
}


@router.get("", response_model=SellerListResponse)
def list_sellers(
    sort: str = Query("avgRisk", description="avgRisk | flaggedReviews | reviews"),
    db: DatabaseConnection = Depends(get_db),
    _user: dict = Depends(require_auth),
):
    """
    Devuelve perfiles de riesgo de vendedores.
    Alimenta directamente a SellersTable.jsx.
    """
    order_col = _SORT_COLS.get(sort, "avg_risk_score")
    rows = db.execute(
        f"""
        SELECT seller_id, seller_name, total_products, total_reviews,
               flagged_reviews, avg_risk_score, risk_level
        FROM seller_risk_profiles
        ORDER BY {order_col} DESC
        LIMIT 100
        """
    )

    sellers = [
        SellerOut(
            id=row["seller_id"],
            name=row["seller_name"],
            rating=float(row["avg_risk_score"]),
            reviews=row["total_reviews"],
            risk=row["risk_level"],
            products=row["total_products"],
            flaggedReviews=row["flagged_reviews"],
        )
        for row in rows
    ]
    return SellerListResponse(sellers=sellers)


@router.get("/{seller_id}", response_model=SellerOut)
def get_seller(
    seller_id: str,
    db: DatabaseConnection = Depends(get_db),
    _user: dict = Depends(require_auth),
):
    rows = db.execute(
        """
        SELECT seller_id, seller_name, total_products, total_reviews,
               flagged_reviews, avg_risk_score, risk_level
        FROM seller_risk_profiles
        WHERE seller_id = %s LIMIT 1
        """,
        (seller_id,),
    )
    if not rows:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")

    row = rows[0]
    return SellerOut(
        id=row["seller_id"],
        name=row["seller_name"],
        rating=float(row["avg_risk_score"]),
        reviews=row["total_reviews"],
        risk=row["risk_level"],
        products=row["total_products"],
        flaggedReviews=row["flagged_reviews"],
    )
