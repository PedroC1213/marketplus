"""
MarketPlus - Pipeline Principal con MySQL
Lee reseñas pendientes de la BD, las analiza y guarda los resultados.

Modos de ejecución:
    python main.py                        # analiza reseñas sin score en la BD
    python main.py --demo                 # inserta datos de prueba y corre el pipeline
    python main.py --model model_weights.json
    python main.py --demo --verbose

Variables de entorno requeridas (o en archivo .env):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.schema import create_tables
from database.repositories import (
    ReviewRepository,
    FraudScoreRepository,
    CampaignRepository,
    SellerProfileRepository,
    AlertRepository,
)
from models.schemas import Review, ReviewMetadata, RiskLevel
from detector.fraud_detector import FraudDetector
from detector.campaign_detector import CampaignDetector
from detector.seller_aggregator import SellerRiskAggregator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Datos demo
# ──────────────────────────────────────────────────────────────

def _make_review(
    product_id, seller_id, rating, text, user,
    ip="200.1.2.3",
    device="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    previous_reviews=5,
    account_age_days=180,
    minutes_ago=0,
    product_name=None,
) -> Review:
    date = datetime.utcnow() - timedelta(minutes=minutes_ago)
    meta = ReviewMetadata(
        ip=ip, device=device, user_id=user, date=date,
        previous_reviews=previous_reviews, account_age_days=account_age_days,
    )
    return Review(
        id=0,
        product=product_name or product_id,
        product_id=product_id,
        seller_id=seller_id,
        rating=rating, text=text, user=user,
        metadata=meta, date=date,
    )


DEMO_SELLERS = [
    ("seller_tech", "TechStore SAS"),
    ("seller_hogar", "Hogar y Más"),
]

DEMO_PRODUCTS = [
    ("p001", "seller_tech", "Laptop Gamer Ultra"),
    ("p002", "seller_tech", "Smartwatch Pro"),
    ("p003", "seller_tech", "Auriculares Bluetooth"),
    ("p004", "seller_hogar", "Cafetera Express"),
    ("p005", "seller_tech", "Smartphone X"),
]

DEMO_REVIEWS = [
    _make_review("p001", "seller_tech", 5, "Excelente producto, lo recomiendo muchísimo",
                 "comp_a", ip="190.12.34.56", previous_reviews=0, account_age_days=2, minutes_ago=10),
    _make_review("p002", "seller_tech", 5, "Excelente producto, lo recomiendo muchísimo",
                 "comp_b", ip="190.12.34.57", previous_reviews=0, account_age_days=2, minutes_ago=15),
    _make_review("p003", "seller_tech", 5, "Excelente producto, lo recomiendo muchísimo",
                 "comp_c", ip="190.12.34.58", previous_reviews=0, account_age_days=3, minutes_ago=20),
    _make_review("p004", "seller_hogar", 5, "Excelente producto, lo recomiendo muchísimo",
                 "comp_d", ip="190.12.34.59", previous_reviews=0, account_age_days=1, minutes_ago=25),
    _make_review("p005", "seller_tech", 5, "Increíble rendimiento, cámara espectacular",
                 "user_bot1", ip="190.12.34.56", previous_reviews=0, account_age_days=5, minutes_ago=5),
    _make_review("p005", "seller_tech", 5, "La batería dura todo el día, perfecto",
                 "user_bot2", ip="190.12.34.56", previous_reviews=0, account_age_days=5, minutes_ago=8),
    _make_review("p005", "seller_tech", 5, "Fantástico, lo mejor que he comprado",
                 "user_bot3", ip="190.12.34.56", previous_reviews=0, account_age_days=4, minutes_ago=12),
    _make_review("p003", "seller_hogar", 1,
                 "No funciona bien, el sonido es muy bajo y se desconecta constantemente.",
                 "user_real1", ip="200.5.6.7", previous_reviews=12, account_age_days=365, minutes_ago=300),
    _make_review("p002", "seller_hogar", 4,
                 "Buen reloj en general. La pantalla es clara y la batería dura dos días.",
                 "user_real2", ip="201.8.9.10", previous_reviews=7, account_age_days=200, minutes_ago=500),
    _make_review("p004", "seller_hogar", 3,
                 "Regular. El café sale a buena temperatura pero el depósito es pequeño.",
                 "user_real3", ip="202.11.12.13", previous_reviews=20, account_age_days=730, minutes_ago=1200),
    _make_review("p001", "seller_tech", 5, "PERFECTO PERFECTO PERFECTO!!! INCREÍBLE!!!",
                 "bot_user", ip="10.0.0.1",
                 device="python-requests/2.28.0",
                 previous_reviews=0, account_age_days=0, minutes_ago=3),
]


def seed_demo_data(db: DatabaseConnection) -> None:
    logger.info("Insertando datos demo...")
    db.execute_many("INSERT IGNORE INTO sellers (id, name) VALUES (%s, %s)", DEMO_SELLERS)
    db.execute_many("INSERT IGNORE INTO products (id, seller_id, name) VALUES (%s, %s, %s)", DEMO_PRODUCTS)
    review_repo = ReviewRepository(db)
    inserted = review_repo.insert_batch(DEMO_REVIEWS)
    logger.info(f"  {inserted} reseñas demo insertadas.")


# ──────────────────────────────────────────────────────────────
# Pipeline principal
# ──────────────────────────────────────────────────────────────

def run_pipeline(db: DatabaseConnection, model_path: str = None, batch_size: int = 200) -> None:
    logger.info("=" * 60)
    logger.info("  MarketPlus — Pipeline de Detección de Fraude (MySQL)")
    logger.info("=" * 60)

    review_repo   = ReviewRepository(db)
    score_repo    = FraudScoreRepository(db)
    campaign_repo = CampaignRepository(db)
    profile_repo  = SellerProfileRepository(db)
    alert_repo    = AlertRepository(db)

    detector = FraudDetector()
    if model_path:
        try:
            detector.load_model(model_path)
            logger.info(f"Modelo ML cargado desde '{model_path}'")
        except FileNotFoundError:
            logger.warning(f"'{model_path}' no encontrado, usando pesos por defecto")

    campaign_detector = CampaignDetector()
    aggregator        = SellerRiskAggregator()

    # 1. Reseñas pendientes
    logger.info(f"\n📥 Leyendo reseñas sin analizar (máx. {batch_size})...")
    reviews = review_repo.get_unscored(limit=batch_size)
    if not reviews:
        logger.info("No hay reseñas pendientes de analizar.")
        return
    logger.info(f"  {len(reviews)} reseñas encontradas.")

    # 2. Analizar
    logger.info("\n🔍 Analizando reseñas...")
    scores = detector.analyze_batch(reviews)

    # 3. Guardar scores
    logger.info("\n💾 Guardando scores en fraud_scores...")
    saved = score_repo.upsert_batch(scores)
    logger.info(f"  {saved} scores guardados.")

    # 4. Detectar campañas
    logger.info("\n🕵️  Detectando campañas...")
    campaigns = campaign_detector.detect(reviews, scores)
    if campaigns:
        n = campaign_repo.insert_batch(campaigns)
        logger.info(f"  {n} campañas nuevas registradas.")
    else:
        logger.info("  Sin campañas nuevas.")

    # 5. Perfiles de vendedores
    logger.info("\n🏪 Actualizando perfiles de vendedores...")
    seller_ids  = list({r.seller_id for r in reviews})
    seller_rows = db.execute(
        f"SELECT id, name FROM sellers WHERE id IN ({','.join(['%s']*len(seller_ids))})",
        tuple(seller_ids),
    )
    seller_names = {row["id"]: row["name"] for row in seller_rows}
    profiles = aggregator.aggregate(reviews, scores, seller_names)
    profile_repo.upsert_batch(profiles)
    logger.info(f"  {len(profiles)} perfiles actualizados.")

    # 6. Alertas
    logger.info("\n🚨 Generando alertas...")
    n_alerts = alert_repo.insert_from_scores(reviews, scores)
    logger.info(f"  {n_alerts} alertas generadas.")

    # Resumen
    risk_counts = {lvl: 0 for lvl in RiskLevel}
    for s in scores:
        risk_counts[s.risk_level] += 1

    print("\n" + "=" * 50)
    print("  RESUMEN DEL PIPELINE")
    print("=" * 50)
    print(f"  Reseñas analizadas : {len(reviews)}")
    print(f"  🔴 Alto riesgo     : {risk_counts[RiskLevel.ALTO]}")
    print(f"  🟡 Medio riesgo    : {risk_counts[RiskLevel.MEDIO]}")
    print(f"  🟢 Bajo riesgo     : {risk_counts[RiskLevel.BAJO]}")
    print(f"  Campañas detectadas: {len(campaigns)}")
    print(f"  Alertas generadas  : {n_alerts}")
    print("=" * 50)
    logger.info("\n✅ Pipeline completado.")


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MarketPlus - Pipeline con MySQL")
    parser.add_argument("--model",   type=str,  default=None,  help="Ruta al model_weights.json")
    parser.add_argument("--demo",    action="store_true",       help="Insertar datos de prueba")
    parser.add_argument("--batch",   type=int,  default=200,   help="Reseñas por ejecución")
    parser.add_argument("--verbose", action="store_true",       help="Logging detallado")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = DatabaseConfig.from_env()
    logger.info(f"Conectando a MySQL: {config}")
    db = DatabaseConnection(config)

    try:
        db.connect()
        if not db.ping():
            logger.error("No se pudo verificar la conexión. Revisa tus credenciales en .env")
            sys.exit(1)

        logger.info("Verificando esquema...")
        create_tables(db)

        if args.demo:
            seed_demo_data(db)

        run_pipeline(db, model_path=args.model, batch_size=args.batch)

    except Exception as e:
        logger.error(f"Error en el pipeline: {e}", exc_info=args.verbose)
        sys.exit(1)
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
