"""
MarketPlus - Extracción de características (features)
Transforma reseñas crudas en vectores numéricos para el modelo de detección de fraude.
"""

import re
import math
from collections import Counter
from typing import List, Dict, Any
from datetime import datetime, timedelta

from models.schemas import Review, ReviewMetadata


# ─────────────────────────────────────────────
# Helpers de texto
# ─────────────────────────────────────────────

def _word_count(text: str) -> int:
    return len(text.split())


def _unique_word_ratio(text: str) -> float:
    """Relación palabras únicas / total. Bajo → texto repetitivo."""
    words = text.lower().split()
    if not words:
        return 1.0
    return len(set(words)) / len(words)


def _contains_superlatives(text: str) -> bool:
    """Detecta adjetivos extremos comunes en reseñas falsas (ES)."""
    patterns = [
        r"\bexcelente\b", r"\bperfecto\b", r"\binmejorable\b",
        r"\bincreíble\b", r"\bfantástico\b", r"\bmaravilloso\b",
        r"\bespectacular\b", r"\bsuperior\b", r"\bextraordinario\b",
    ]
    text_lower = text.lower()
    return sum(1 for p in patterns if re.search(p, text_lower)) >= 2


def _exclamation_ratio(text: str) -> float:
    """Ratio de signos de exclamación sobre longitud del texto."""
    if not text:
        return 0.0
    return text.count("!") / len(text)


def _capitalized_word_ratio(text: str) -> float:
    words = text.split()
    if not words:
        return 0.0
    caps = sum(1 for w in words if w.isupper() and len(w) > 1)
    return caps / len(words)


def _character_entropy(text: str) -> float:
    """Entropía de Shannon a nivel de caracteres. Texto generado suele tener entropía baja."""
    if not text:
        return 0.0
    counts = Counter(text)
    total = len(text)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


# ─────────────────────────────────────────────
# Features de texto
# ─────────────────────────────────────────────

def extract_text_features(text: str) -> Dict[str, float]:
    """
    Extrae características lingüísticas de la reseña.

    Returns:
        Dict con claves numéricas, todas en [0, 1] salvo donde se indique.
    """
    return {
        "word_count": min(_word_count(text) / 200, 1.0),          # normalizado a 200 palabras
        "unique_word_ratio": _unique_word_ratio(text),
        "has_superlatives": float(_contains_superlatives(text)),
        "exclamation_ratio": min(_exclamation_ratio(text) * 10, 1.0),
        "caps_ratio": _capitalized_word_ratio(text),
        "text_entropy": min(_character_entropy(text) / 5.0, 1.0), # entropía normalizada
        "is_very_short": float(_word_count(text) < 5),
        "is_very_long": float(_word_count(text) > 150),
    }


# ─────────────────────────────────────────────
# Features de metadatos / comportamiento
# ─────────────────────────────────────────────

def extract_metadata_features(meta: ReviewMetadata) -> Dict[str, float]:
    """
    Extrae señales de comportamiento del usuario y dispositivo.
    """
    # Cuenta de reseñas previas del usuario (0 previas = cuenta nueva)
    prev_reviews_norm = min(meta.previous_reviews / 50, 1.0)
    new_account = float(meta.account_age_days < 7)
    
    # IP sospechosa: rangos privados o IPs con patrón de bot (simplificado)
    suspicious_ip = float(_is_suspicious_ip(meta.ip))

    # User-agent headless o automatizado
    headless_ua = float(_is_headless_agent(meta.device))

    return {
        "new_account": new_account,
        "prev_reviews_norm": prev_reviews_norm,
        "no_prior_reviews": float(meta.previous_reviews == 0),
        "suspicious_ip": suspicious_ip,
        "headless_user_agent": headless_ua,
    }


def _is_suspicious_ip(ip: str) -> bool:
    """Detecta patrones de IP comúnmente asociados a VPN/proxy/bot (heurística simple)."""
    suspicious_prefixes = ["10.", "172.", "192.168.", "127.", "0.0.0.0"]
    return any(ip.startswith(p) for p in suspicious_prefixes)


def _is_headless_agent(user_agent: str) -> bool:
    """Detecta user-agents de bots, scrapers o navegadores headless."""
    bot_signals = ["headlesschrome", "phantomjs", "selenium", "puppeteer",
                   "python-requests", "curl", "wget", "scrapy", "bot", "spider"]
    ua_lower = user_agent.lower()
    return any(sig in ua_lower for sig in bot_signals)


# ─────────────────────────────────────────────
# Features de contexto (en relación a otras reseñas)
# ─────────────────────────────────────────────

def extract_context_features(
    review: Review,
    recent_reviews: List[Review],
    time_window_minutes: int = 60,
) -> Dict[str, float]:
    """
    Detecta patrones coordinados comparando con reseñas recientes del mismo producto/vendedor.

    Args:
        review: Reseña actual.
        recent_reviews: Lista de reseñas recientes del mismo producto o vendedor.
        time_window_minutes: Ventana de tiempo para buscar patrones.
    """
    cutoff = review.date - timedelta(minutes=time_window_minutes)
    window = [r for r in recent_reviews if r.date >= cutoff and r.id != review.id]

    # Reseñas del mismo producto en la ventana
    same_product = [r for r in window if r.product_id == review.product_id]

    # Textos duplicados o muy similares
    duplicate_texts = _count_similar_texts(review.text, [r.text for r in same_product])

    # Misma IP en el producto
    same_ip_count = sum(1 for r in same_product if r.metadata.ip == review.metadata.ip)

    # Ráfaga de 5 estrellas
    five_star_burst = sum(1 for r in same_product if r.rating == 5)

    # Nuevas cuentas publicando simultáneamente
    new_accounts_burst = sum(1 for r in same_product if r.metadata.previous_reviews == 0)

    return {
        "burst_in_window": min(len(same_product) / 20, 1.0),
        "duplicate_text_count": min(duplicate_texts / 10, 1.0),
        "same_ip_count": min(same_ip_count / 5, 1.0),
        "five_star_burst": min(five_star_burst / 10, 1.0),
        "new_accounts_burst": min(new_accounts_burst / 10, 1.0),
    }


def _count_similar_texts(target: str, texts: List[str], threshold: float = 0.8) -> int:
    """
    Cuenta cuántos textos tienen similitud de Jaccard con el objetivo por encima del umbral.
    """
    target_tokens = set(target.lower().split())
    count = 0
    for text in texts:
        tokens = set(text.lower().split())
        union = target_tokens | tokens
        if not union:
            continue
        similarity = len(target_tokens & tokens) / len(union)
        if similarity >= threshold:
            count += 1
    return count


# ─────────────────────────────────────────────
# Vector completo
# ─────────────────────────────────────────────

def build_feature_vector(
    review: Review,
    recent_reviews: List[Review],
    time_window_minutes: int = 60,
) -> Dict[str, float]:
    """
    Combina todos los grupos de features en un único diccionario.
    """
    text_feats = extract_text_features(review.text)
    meta_feats = extract_metadata_features(review.metadata)
    ctx_feats = extract_context_features(review, recent_reviews, time_window_minutes)

    return {**text_feats, **meta_feats, **ctx_feats}


def feature_vector_to_list(features: Dict[str, float]) -> List[float]:
    """Convierte el diccionario de features a lista ordenada (para ML clásico)."""
    keys = sorted(features.keys())
    return [features[k] for k in keys]


FEATURE_NAMES = sorted([
    # Texto
    "word_count", "unique_word_ratio", "has_superlatives",
    "exclamation_ratio", "caps_ratio", "text_entropy",
    "is_very_short", "is_very_long",
    # Metadatos
    "new_account", "prev_reviews_norm", "no_prior_reviews",
    "suspicious_ip", "headless_user_agent",
    # Contexto
    "burst_in_window", "duplicate_text_count", "same_ip_count",
    "five_star_burst", "new_accounts_burst",
])
