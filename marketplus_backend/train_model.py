"""
MarketPlus - Entrenamiento del Modelo
Genera datos sintéticos etiquetados y entrena el modelo de regresión logística.
Guarda los pesos en model_weights.json para que FraudDetector los cargue.

Uso:
    python train_model.py
    python train_model.py --output my_weights.json --samples 5000
"""

import json
import math
import random
import argparse
import logging
from typing import List, Tuple, Dict

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Generación de datos sintéticos
# ─────────────────────────────────────────────

FEATURE_NAMES = sorted([
    "burst_in_window", "caps_ratio", "duplicate_text_count",
    "exclamation_ratio", "five_star_burst", "has_superlatives",
    "headless_user_agent", "is_very_long", "is_very_short",
    "new_account", "new_accounts_burst", "no_prior_reviews",
    "prev_reviews_norm", "same_ip_count", "suspicious_ip",
    "text_entropy", "unique_word_ratio", "word_count",
])


def _rnd(lo: float, hi: float) -> float:
    return random.uniform(lo, hi)


def generate_synthetic_sample(label: int) -> Tuple[Dict[str, float], int]:
    """
    Genera un vector de features con características típicas de reseña
    fraudulenta (label=1) o legítima (label=0).
    """
    if label == 1:
        # Reseña fraudulenta: features "malas"
        features = {
            "burst_in_window": _rnd(0.3, 1.0),
            "caps_ratio": _rnd(0.0, 0.15),
            "duplicate_text_count": _rnd(0.2, 1.0),
            "exclamation_ratio": _rnd(0.1, 0.6),
            "five_star_burst": _rnd(0.3, 1.0),
            "has_superlatives": random.choice([0.0, 0.0, 1.0, 1.0, 1.0]),
            "headless_user_agent": random.choice([0.0, 0.0, 0.0, 1.0]),
            "is_very_long": 0.0,
            "is_very_short": random.choice([0.0, 1.0]),
            "new_account": random.choice([0.0, 1.0, 1.0]),
            "new_accounts_burst": _rnd(0.2, 1.0),
            "no_prior_reviews": random.choice([1.0, 1.0, 0.0]),
            "prev_reviews_norm": _rnd(0.0, 0.1),
            "same_ip_count": _rnd(0.2, 1.0),
            "suspicious_ip": random.choice([0.0, 0.0, 1.0]),
            "text_entropy": _rnd(0.2, 0.5),
            "unique_word_ratio": _rnd(0.2, 0.55),
            "word_count": _rnd(0.0, 0.15),
        }
    else:
        # Reseña legítima: features "buenas"
        features = {
            "burst_in_window": _rnd(0.0, 0.2),
            "caps_ratio": _rnd(0.0, 0.05),
            "duplicate_text_count": _rnd(0.0, 0.1),
            "exclamation_ratio": _rnd(0.0, 0.1),
            "five_star_burst": _rnd(0.0, 0.2),
            "has_superlatives": random.choice([0.0, 0.0, 0.0, 1.0]),
            "headless_user_agent": 0.0,
            "is_very_long": random.choice([0.0, 0.0, 1.0]),
            "is_very_short": random.choice([0.0, 0.0, 0.0, 1.0]),
            "new_account": random.choice([0.0, 0.0, 1.0]),
            "new_accounts_burst": _rnd(0.0, 0.15),
            "no_prior_reviews": random.choice([0.0, 1.0]),
            "prev_reviews_norm": _rnd(0.2, 1.0),
            "same_ip_count": _rnd(0.0, 0.1),
            "suspicious_ip": 0.0,
            "text_entropy": _rnd(0.55, 1.0),
            "unique_word_ratio": _rnd(0.55, 1.0),
            "word_count": _rnd(0.1, 0.8),
        }
    return features, label


def generate_dataset(n_samples: int, fraud_ratio: float = 0.3):
    """Genera dataset balanceado según fraud_ratio."""
    n_fraud = int(n_samples * fraud_ratio)
    samples = (
        [generate_synthetic_sample(1) for _ in range(n_fraud)]
        + [generate_synthetic_sample(0) for _ in range(n_samples - n_fraud)]
    )
    random.shuffle(samples)
    return samples


# ─────────────────────────────────────────────
# Regresión Logística desde cero
# ─────────────────────────────────────────────

def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-500, min(500, x))))


def predict(weights: Dict[str, float], bias: float, features: Dict[str, float]) -> float:
    z = bias + sum(weights[k] * features.get(k, 0.0) for k in FEATURE_NAMES)
    return sigmoid(z)


def binary_cross_entropy(y_true: int, y_pred: float) -> float:
    eps = 1e-9
    return -(y_true * math.log(y_pred + eps) + (1 - y_true) * math.log(1 - y_pred + eps))


def train(
    dataset: List[Tuple[Dict[str, float], int]],
    lr: float = 0.05,
    epochs: int = 100,
    l2_lambda: float = 0.01,
) -> Tuple[Dict[str, float], float]:
    """
    Entrena regresión logística con gradiente descendente estocástico.

    Returns:
        (weights dict, bias)
    """
    weights = {k: 0.0 for k in FEATURE_NAMES}
    bias = 0.0

    for epoch in range(1, epochs + 1):
        random.shuffle(dataset)
        total_loss = 0.0

        for features, label in dataset:
            y_pred = predict(weights, bias, features)
            error = y_pred - label
            total_loss += binary_cross_entropy(label, y_pred)

            # Actualizar pesos con L2 regularización
            for k in FEATURE_NAMES:
                grad = error * features.get(k, 0.0) + l2_lambda * weights[k]
                weights[k] -= lr * grad
            bias -= lr * error

        if epoch % 10 == 0:
            avg_loss = total_loss / len(dataset)
            accuracy = evaluate_accuracy(dataset, weights, bias)
            logger.info(f"Epoch {epoch:3d}/{epochs} | loss={avg_loss:.4f} | acc={accuracy:.3f}")

    return weights, bias


def evaluate_accuracy(
    dataset: List[Tuple[Dict[str, float], int]],
    weights: Dict[str, float],
    bias: float,
    threshold: float = 0.5,
) -> float:
    correct = sum(
        1 for features, label in dataset
        if (predict(weights, bias, features) >= threshold) == bool(label)
    )
    return correct / len(dataset)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Entrena el modelo de detección de fraude")
    parser.add_argument("--samples", type=int, default=3000, help="Número de muestras sintéticas")
    parser.add_argument("--epochs", type=int, default=150, help="Épocas de entrenamiento")
    parser.add_argument("--lr", type=float, default=0.05, help="Learning rate")
    parser.add_argument("--fraud-ratio", type=float, default=0.3, help="Proporción de fraude en el dataset")
    parser.add_argument("--output", type=str, default="model_weights.json", help="Ruta de salida del modelo")
    args = parser.parse_args()

    logger.info(f"Generando {args.samples} muestras (fraude: {args.fraud_ratio:.0%})...")
    dataset = generate_dataset(args.samples, args.fraud_ratio)

    # Split 80/20 train/test
    split = int(len(dataset) * 0.8)
    train_set, test_set = dataset[:split], dataset[split:]

    logger.info(f"Entrenando: {len(train_set)} train | {len(test_set)} test")
    weights, bias = train(train_set, lr=args.lr, epochs=args.epochs)

    test_acc = evaluate_accuracy(test_set, weights, bias)
    logger.info(f"\n✅ Accuracy en test: {test_acc:.3f}")

    # Guardar modelo
    payload = {"weights": weights, "bias": bias}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info(f"Modelo guardado en '{args.output}'")

    # Top features por importancia (|peso|)
    top_features = sorted(weights.items(), key=lambda x: abs(x[1]), reverse=True)[:8]
    logger.info("\nTop features por importancia:")
    for feat, w in top_features:
        logger.info(f"  {feat:<30} {w:+.4f}")


if __name__ == "__main__":
    main()
