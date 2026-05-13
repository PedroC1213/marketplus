"""
MarketPlus - Detector de Fraude
Motor principal de scoring que combina reglas heurísticas con un modelo ML ligero.
Devuelve RiskLevel (Bajo / Medio / Alto) y score 0–1 alineado con el frontend.
"""

import logging
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from models.schemas import Review, FraudScore, RiskLevel
from features.extractor import build_feature_vector, feature_vector_to_list, FEATURE_NAMES

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Reglas heurísticas (capa rápida, interpretable)
# ─────────────────────────────────────────────

class RuleEngine:
    """
    Conjunto de reglas deterministas.
    Cada regla retorna (contribución_score: float, razón: str | None).
    """

    RULES: List[Dict[str, Any]] = [
        {
            "name": "texto_duplicado",
            "description": "Texto idéntico o casi idéntico en múltiples reseñas",
            "feature": "duplicate_text_count",
            "thresholds": [(0.3, 0.4, "Texto similar en ≥3 reseñas recientes"),
                           (0.1, 0.25, "Texto similar en 1–2 reseñas recientes")],
        },
        {
            "name": "rafaga_ip",
            "description": "Múltiples reseñas desde la misma IP",
            "feature": "same_ip_count",
            "thresholds": [(0.4, 0.5, "≥2 reseñas desde la misma IP en ventana reciente")],
        },
        {
            "name": "cuenta_nueva",
            "description": "Cuenta recién creada sin historial",
            "feature": "new_account",
            "thresholds": [(0.5, 0.2, "Cuenta con menos de 7 días de antigüedad")],
        },
        {
            "name": "sin_reseñas_previas",
            "description": "Primera reseña de un usuario",
            "feature": "no_prior_reviews",
            "thresholds": [(0.5, 0.1, "Usuario sin reseñas anteriores")],
        },
        {
            "name": "rafaga_5_estrellas",
            "description": "Ráfaga de valoraciones perfectas en poco tiempo",
            "feature": "five_star_burst",
            "thresholds": [(0.4, 0.4, "≥4 reseñas de 5★ en ventana reciente"),
                           (0.2, 0.2, "2–3 reseñas de 5★ en ventana reciente")],
        },
        {
            "name": "rafaga_cuentas_nuevas",
            "description": "Varias cuentas nuevas publican en el mismo producto",
            "feature": "new_accounts_burst",
            "thresholds": [(0.4, 0.35, "≥4 cuentas nuevas publicando a la vez")],
        },
        {
            "name": "superlativos",
            "description": "Lenguaje excesivamente positivo / marketing",
            "feature": "has_superlatives",
            "thresholds": [(0.5, 0.15, "Uso excesivo de adjetivos superlativos")],
        },
        {
            "name": "ip_sospechosa",
            "description": "IP de VPN, proxy o rango interno",
            "feature": "suspicious_ip",
            "thresholds": [(0.5, 0.2, "IP asociada a VPN, proxy o rango privado")],
        },
        {
            "name": "agente_headless",
            "description": "User-agent de bot o navegador automatizado",
            "feature": "headless_user_agent",
            "thresholds": [(0.5, 0.45, "User-agent de bot o scraper detectado")],
        },
        {
            "name": "rafaga_producto",
            "description": "Muchas reseñas en poco tiempo para el mismo producto",
            "feature": "burst_in_window",
            "thresholds": [(0.6, 0.3, "≥12 reseñas en el producto en la última hora"),
                           (0.3, 0.15, "≥6 reseñas en el producto en la última hora")],
        },
    ]

    def evaluate(self, features: Dict[str, float]) -> tuple[float, List[str]]:
        """
        Aplica todas las reglas.

        Returns:
            (score acumulado sin normalizar, lista de razones activadas)
        """
        total_score = 0.0
        reasons = []

        for rule in self.RULES:
            feat_val = features.get(rule["feature"], 0.0)
            for threshold, contribution, reason_text in rule["thresholds"]:
                if feat_val >= threshold:
                    total_score += contribution
                    reasons.append(reason_text)
                    break  # solo la primera condición que se cumple por regla

        return min(total_score, 1.0), reasons


# ─────────────────────────────────────────────
# Modelo ML ligero (Regresión Logística)
# ─────────────────────────────────────────────

class SimpleMLModel:
    """
    Modelo de regresión logística entrenado con datos sintéticos.
    En producción, reemplaza los pesos con un modelo entrenado real
    usando `train_model.py`.
    """

    # Pesos por feature (orden: FEATURE_NAMES sorted)
    # Valores iniciales calibrados manualmente como prior razonable
    DEFAULT_WEIGHTS: Dict[str, float] = {
        "burst_in_window": 1.8,
        "caps_ratio": 0.5,
        "duplicate_text_count": 2.5,
        "exclamation_ratio": 0.4,
        "five_star_burst": 1.6,
        "has_superlatives": 0.9,
        "headless_user_agent": 2.2,
        "is_very_long": -0.3,
        "is_very_short": 0.6,
        "new_account": 0.8,
        "new_accounts_burst": 1.7,
        "no_prior_reviews": 0.5,
        "prev_reviews_norm": -0.6,
        "same_ip_count": 2.0,
        "suspicious_ip": 1.0,
        "text_entropy": -0.7,
        "unique_word_ratio": -1.2,
        "word_count": -0.4,
    }
    BIAS: float = -2.0

    def __init__(self, weights: Optional[Dict[str, float]] = None, bias: float = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.bias = bias if bias is not None else self.BIAS

    @staticmethod
    def _sigmoid(x: float) -> float:
        import math
        return 1.0 / (1.0 + math.exp(-x))

    def predict_proba(self, features: Dict[str, float]) -> float:
        """Retorna probabilidad de fraude (0–1)."""
        z = self.bias
        for feat_name, weight in self.weights.items():
            z += weight * features.get(feat_name, 0.0)
        return self._sigmoid(z)

    def save(self, path: str) -> None:
        """Guarda pesos en JSON."""
        payload = {"weights": self.weights, "bias": self.bias}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Modelo guardado en {path}")

    @classmethod
    def load(cls, path: str) -> "SimpleMLModel":
        """Carga pesos desde JSON."""
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return cls(weights=payload["weights"], bias=payload["bias"])


# ─────────────────────────────────────────────
# Detector principal
# ─────────────────────────────────────────────

class FraudDetector:
    """
    Orquesta el pipeline completo:
        1. Extracción de features
        2. Evaluación de reglas heurísticas
        3. Score del modelo ML
        4. Combinación → RiskLevel final
    """

    # Umbrales para clasificar el score final
    THRESHOLD_ALTO = 0.65
    THRESHOLD_MEDIO = 0.35

    # Peso relativo entre reglas y modelo ML (0 = solo reglas, 1 = solo ML)
    ML_BLEND_WEIGHT = 0.45

    def __init__(self, model: Optional[SimpleMLModel] = None):
        self.rule_engine = RuleEngine()
        self.model = model or SimpleMLModel()

    # ── API principal ──────────────────────────────────────────

    def analyze(
        self,
        review: Review,
        recent_reviews: Optional[List[Review]] = None,
        time_window_minutes: int = 60,
    ) -> FraudScore:
        """
        Analiza una reseña individual y devuelve su FraudScore.

        Args:
            review: Reseña a analizar.
            recent_reviews: Contexto de reseñas recientes para detectar patrones grupales.
            time_window_minutes: Ventana temporal para análisis de contexto.
        """
        recent_reviews = recent_reviews or []

        # 1. Extraer features
        features = build_feature_vector(review, recent_reviews, time_window_minutes)

        # 2. Reglas heurísticas
        rule_score, reasons = self.rule_engine.evaluate(features)

        # 3. Modelo ML
        ml_score = self.model.predict_proba(features)

        # 4. Combinar scores
        final_score = (
            (1 - self.ML_BLEND_WEIGHT) * rule_score
            + self.ML_BLEND_WEIGHT * ml_score
        )
        final_score = round(min(max(final_score, 0.0), 1.0), 4)

        # 5. Clasificar nivel de riesgo
        risk_level = self._score_to_risk(final_score)

        logger.debug(
            f"[review={review.id}] rule={rule_score:.3f} ml={ml_score:.3f} "
            f"final={final_score:.3f} risk={risk_level}"
        )

        return FraudScore(
            review_id=review.id,
            risk_level=risk_level,
            score=final_score,
            reasons=reasons,
            analyzed_at=datetime.utcnow(),
        )

    def analyze_batch(
        self,
        reviews: List[Review],
        time_window_minutes: int = 60,
    ) -> List[FraudScore]:
        """
        Analiza un lote de reseñas. Cada reseña usa las demás como contexto.
        """
        results: List[FraudScore] = []
        for review in reviews:
            context = [r for r in reviews if r.id != review.id]
            score = self.analyze(review, context, time_window_minutes)
            results.append(score)
        return results

    # ── Internos ──────────────────────────────────────────────

    def _score_to_risk(self, score: float) -> RiskLevel:
        if score >= self.THRESHOLD_ALTO:
            return RiskLevel.ALTO
        elif score >= self.THRESHOLD_MEDIO:
            return RiskLevel.MEDIO
        return RiskLevel.BAJO

    # ── Configuración ─────────────────────────────────────────

    def set_thresholds(self, alto: float, medio: float) -> None:
        """Permite ajustar umbrales sin reentrenar."""
        assert 0 < medio < alto <= 1.0, "Umbrales inválidos"
        self.THRESHOLD_ALTO = alto
        self.THRESHOLD_MEDIO = medio

    def load_model(self, path: str) -> None:
        """Carga un modelo entrenado desde archivo JSON."""
        self.model = SimpleMLModel.load(path)
        logger.info(f"Modelo cargado desde {path}")
