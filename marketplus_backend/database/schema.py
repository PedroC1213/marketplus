"""
MarketPlus - Esquema de Base de Datos MySQL
Crea todas las tablas necesarias si no existen.

Uso:
    python -m database.schema          # usa .env
    python -m database.schema --drop   # elimina y recrea todas las tablas (¡cuidado!)
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.config import DatabaseConfig
from database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# DDL — definición de tablas
# ──────────────────────────────────────────────────────────────

TABLES = {

    "sellers": """
        CREATE TABLE IF NOT EXISTS sellers (
            id          VARCHAR(64)     NOT NULL,
            name        VARCHAR(255)    NOT NULL,
            created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    "products": """
        CREATE TABLE IF NOT EXISTS products (
            id          VARCHAR(64)     NOT NULL,
            seller_id   VARCHAR(64)     NOT NULL,
            name        VARCHAR(255)    NOT NULL,
            created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            INDEX idx_seller (seller_id),
            CONSTRAINT fk_product_seller
                FOREIGN KEY (seller_id) REFERENCES sellers(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    "reviews": """
        CREATE TABLE IF NOT EXISTS reviews (
            id                  INT             NOT NULL AUTO_INCREMENT,
            product_id          VARCHAR(64)     NOT NULL,
            seller_id           VARCHAR(64)     NOT NULL,
            user_id             VARCHAR(128)    NOT NULL,
            rating              TINYINT         NOT NULL CHECK (rating BETWEEN 1 AND 5),
            text                TEXT            NOT NULL,
            ip                  VARCHAR(45)     NOT NULL,   -- soporta IPv6
            device              VARCHAR(512)    NOT NULL,
            previous_reviews    INT             NOT NULL DEFAULT 0,
            account_age_days    INT             NOT NULL DEFAULT 0,
            review_date         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            INDEX idx_product   (product_id),
            INDEX idx_seller    (seller_id),
            INDEX idx_user      (user_id),
            INDEX idx_ip        (ip),
            INDEX idx_date      (review_date),
            CONSTRAINT fk_review_product
                FOREIGN KEY (product_id) REFERENCES products(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_review_seller
                FOREIGN KEY (seller_id) REFERENCES sellers(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    "fraud_scores": """
        CREATE TABLE IF NOT EXISTS fraud_scores (
            id              INT             NOT NULL AUTO_INCREMENT,
            review_id       INT             NOT NULL,
            risk_level      ENUM('Bajo','Medio','Alto') NOT NULL,
            score           DECIMAL(6,4)    NOT NULL,
            reasons         JSON            NOT NULL,       -- lista de strings
            campaign_id     INT             NULL,
            analyzed_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_review (review_id),              -- 1 score por reseña
            INDEX idx_risk  (risk_level),
            INDEX idx_score (score),
            CONSTRAINT fk_score_review
                FOREIGN KEY (review_id) REFERENCES reviews(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    "fraud_campaigns": """
        CREATE TABLE IF NOT EXISTS fraud_campaigns (
            id              INT             NOT NULL AUTO_INCREMENT,
            description     TEXT            NOT NULL,
            severity        ENUM('Bajo','Medio','Alto') NOT NULL,
            seller_id       VARCHAR(64)     NULL,
            review_ids      JSON            NOT NULL,       -- lista de ints
            status          ENUM('activa','en revisión','cerrada') NOT NULL DEFAULT 'activa',
            detected_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            INDEX idx_severity  (severity),
            INDEX idx_status    (status),
            INDEX idx_seller    (seller_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    "seller_risk_profiles": """
        CREATE TABLE IF NOT EXISTS seller_risk_profiles (
            id              INT             NOT NULL AUTO_INCREMENT,
            seller_id       VARCHAR(64)     NOT NULL,
            seller_name     VARCHAR(255)    NOT NULL,
            total_products  INT             NOT NULL DEFAULT 0,
            total_reviews   INT             NOT NULL DEFAULT 0,
            flagged_reviews INT             NOT NULL DEFAULT 0,
            avg_risk_score  DECIMAL(6,4)    NOT NULL DEFAULT 0,
            risk_level      ENUM('Bajo','Medio','Alto') NOT NULL,
            top_reasons     JSON            NOT NULL,
            updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_seller (seller_id),
            INDEX idx_risk  (risk_level),
            INDEX idx_score (avg_risk_score),
            CONSTRAINT fk_profile_seller
                FOREIGN KEY (seller_id) REFERENCES sellers(id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,

    "alerts": """
        CREATE TABLE IF NOT EXISTS alerts (
            id              INT             NOT NULL AUTO_INCREMENT,
            product_id      VARCHAR(64)     NOT NULL,
            product_name    VARCHAR(255)    NOT NULL,
            risk            ENUM('Bajo','Medio','Alto') NOT NULL,
            reason          TEXT            NOT NULL,
            created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            INDEX idx_risk      (risk),
            INDEX idx_product   (product_id),
            INDEX idx_date      (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
}

DROP_ORDER = [
    "alerts", "seller_risk_profiles", "fraud_campaigns",
    "fraud_scores", "reviews", "products", "sellers",
]

CREATE_ORDER = [
    "sellers", "products", "reviews",
    "fraud_scores", "fraud_campaigns",
    "seller_risk_profiles", "alerts",
]


# ──────────────────────────────────────────────────────────────
# Funciones públicas
# ──────────────────────────────────────────────────────────────

def create_tables(db: DatabaseConnection) -> None:
    """Crea todas las tablas si no existen."""
    for table_name in CREATE_ORDER:
        sql = TABLES[table_name]
        with db.cursor() as cur:
            cur.execute(sql)
        logger.info(f"  ✅ Tabla '{table_name}' lista.")


def drop_tables(db: DatabaseConnection) -> None:
    """Elimina todas las tablas en orden seguro (respeta FK)."""
    with db.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table_name in DROP_ORDER:
        with db.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        logger.info(f"  🗑️  Tabla '{table_name}' eliminada.")
    with db.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="Inicializar esquema MarketPlus en MySQL")
    parser.add_argument("--drop", action="store_true",
                        help="Eliminar y recrear todas las tablas (CUIDADO: borra datos)")
    args = parser.parse_args()

    config = DatabaseConfig.from_env()
    logger.info(f"Conectando a {config}")
    db = DatabaseConnection(config)
    db.connect()

    if args.drop:
        confirm = input("⚠️  Esto borrará TODOS los datos. Escribe 'SI' para confirmar: ")
        if confirm.strip().upper() != "SI":
            print("Cancelado.")
            return
        logger.info("Eliminando tablas...")
        drop_tables(db)

    logger.info("Creando tablas...")
    create_tables(db)
    logger.info("✅ Esquema inicializado correctamente.")


if __name__ == "__main__":
    main()
