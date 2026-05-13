"""
MarketPlus - Detector de Campañas
Agrupa reseñas sospechosas individuales en campañas coordinadas.
Implementa los patrones visibles en el frontend (CampaignsList.jsx):
  - Mismo texto repetido en múltiples productos
  - Ráfaga de ★★★★★ desde misma IP
  - Cuentas creadas el mismo día publicando en simultáneo
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from itertools import combinations

from models.schemas import Review, FraudScore, FraudCampaign, RiskLevel

logger = logging.getLogger(__name__)


def _jaccard(text_a: str, text_b: str) -> float:
    """Similitud de Jaccard entre dos textos a nivel de tokens."""
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    union = tokens_a | tokens_b
    if not union:
        return 0.0
    return len(tokens_a & tokens_b) / len(union)


class CampaignDetector:
    """
    Analiza conjuntos de reseñas y detecta campañas de fraude coordinado.
    """

    # Umbrales configurables
    DUPLICATE_TEXT_THRESHOLD = 0.80       # Jaccard mínima para considerar textos iguales
    MIN_CAMPAIGN_SIZE = 3                 # Reseñas mínimas para declarar una campaña
    BURST_WINDOW_MINUTES = 60            # Ventana para ráfaga de IP
    BURST_IP_MIN_REVIEWS = 3             # Reviews desde misma IP para alertar
    NEW_ACCOUNT_WINDOW_DAYS = 1          # Cuentas creadas en el mismo día
    NEW_ACCOUNT_BURST_MIN = 3            # Mínimo de cuentas nuevas sincronizadas

    def __init__(self):
        self._next_campaign_id = 1

    # ── API principal ──────────────────────────────────────────

    def detect(
        self,
        reviews: List[Review],
        fraud_scores: Optional[List[FraudScore]] = None,
    ) -> List[FraudCampaign]:
        """
        Detecta campañas en un conjunto de reseñas.

        Args:
            reviews: Reseñas a analizar.
            fraud_scores: Scores opcionales para filtrar por riesgo previo.

        Returns:
            Lista de FraudCampaign detectadas.
        """
        campaigns: List[FraudCampaign] = []

        # Filtrar por reseñas de riesgo medio/alto si se proveen scores
        if fraud_scores:
            risky_ids = {
                s.review_id for s in fraud_scores
                if s.risk_level != RiskLevel.BAJO
            }
            candidate_reviews = [r for r in reviews if r.id in risky_ids]
        else:
            candidate_reviews = reviews

        if not candidate_reviews:
            return campaigns

        # Detectar cada tipo de campaña
        campaigns += self._detect_duplicate_text_campaigns(candidate_reviews)
        campaigns += self._detect_ip_burst_campaigns(candidate_reviews)
        campaigns += self._detect_new_account_campaigns(candidate_reviews)

        # Deduplicar campañas con mucho solapamiento
        campaigns = self._deduplicate(campaigns)

        logger.info(f"Detectadas {len(campaigns)} campañas en {len(reviews)} reseñas")
        return campaigns

    # ── Estrategias de detección ───────────────────────────────

    def _detect_duplicate_text_campaigns(
        self, reviews: List[Review]
    ) -> List[FraudCampaign]:
        """
        Agrupa reseñas con textos casi idénticos (Jaccard ≥ threshold).
        Patrón: 'Mismo texto "excelente producto" repetido 15 veces'.
        """
        # Grafo de similitud: aristas entre pares muy similares
        similar_pairs: Dict[int, set] = defaultdict(set)
        for a, b in combinations(reviews, 2):
            sim = _jaccard(a.text, b.text)
            if sim >= self.DUPLICATE_TEXT_THRESHOLD:
                similar_pairs[a.id].add(b.id)
                similar_pairs[b.id].add(a.id)

        # Componentes conexas (clusters)
        clusters = self._connected_components(similar_pairs, set(r.id for r in reviews))
        review_map = {r.id: r for r in reviews}

        campaigns = []
        for cluster in clusters:
            if len(cluster) < self.MIN_CAMPAIGN_SIZE:
                continue
            cluster_reviews = [review_map[rid] for rid in cluster]
            severity = self._cluster_severity(cluster_reviews)
            desc = (
                f'Mismo texto repetido {len(cluster)} veces en '
                f'{len({r.product_id for r in cluster_reviews})} productos distintos'
            )
            campaigns.append(self._make_campaign(cluster, severity, desc, cluster_reviews))

        return campaigns

    def _detect_ip_burst_campaigns(
        self, reviews: List[Review]
    ) -> List[FraudCampaign]:
        """
        Detecta ráfagas de reseñas desde la misma IP en ventana de tiempo corta.
        Patrón: 'Ráfaga de reseñas 5★ desde misma IP en 1 hora'.
        """
        # Agrupar por IP → producto
        ip_product_map: Dict[Tuple[str, str], List[Review]] = defaultdict(list)
        for r in reviews:
            key = (r.metadata.ip, r.product_id)
            ip_product_map[key].append(r)

        campaigns = []
        for (ip, product_id), group in ip_product_map.items():
            # Ordenar por fecha y buscar ventanas
            group.sort(key=lambda r: r.date)
            burst = self._find_burst(group, self.BURST_WINDOW_MINUTES)
            if len(burst) >= self.BURST_IP_MIN_REVIEWS:
                ids = {r.id for r in burst}
                severity = RiskLevel.ALTO if len(burst) >= 5 else RiskLevel.MEDIO
                desc = (
                    f'Ráfaga de {len(burst)} reseñas ★★★★★ '
                    f'desde IP {ip} en {self.BURST_WINDOW_MINUTES} minutos'
                )
                campaigns.append(self._make_campaign(ids, severity, desc, burst))

        return campaigns

    def _detect_new_account_campaigns(
        self, reviews: List[Review]
    ) -> List[FraudCampaign]:
        """
        Detecta grupos de cuentas recién creadas que publican en el mismo producto.
        Patrón: 'Cuentas creadas el mismo día publican reseñas positivas idénticas'.
        """
        # Cuentas nuevas
        new_accounts = [
            r for r in reviews
            if r.metadata.account_age_days <= self.NEW_ACCOUNT_WINDOW_DAYS
            or r.metadata.previous_reviews == 0
        ]

        # Agrupar por producto
        by_product: Dict[str, List[Review]] = defaultdict(list)
        for r in new_accounts:
            by_product[r.product_id].append(r)

        campaigns = []
        for product_id, group in by_product.items():
            if len(group) < self.NEW_ACCOUNT_BURST_MIN:
                continue
            ids = {r.id for r in group}
            severity = RiskLevel.ALTO if len(group) >= 6 else RiskLevel.MEDIO
            desc = (
                f'{len(group)} cuentas sin historial publicaron '
                f'reseñas positivas idénticas en el mismo producto'
            )
            campaigns.append(self._make_campaign(ids, severity, desc, group))

        return campaigns

    # ── Utilidades internas ────────────────────────────────────

    def _make_campaign(
        self,
        review_ids,
        severity: RiskLevel,
        description: str,
        reviews: List[Review],
    ) -> FraudCampaign:
        seller_ids = {r.seller_id for r in reviews}
        seller_id = list(seller_ids)[0] if len(seller_ids) == 1 else None
        cid = self._next_campaign_id
        self._next_campaign_id += 1
        return FraudCampaign(
            campaign_id=cid,
            description=description,
            review_ids=sorted(review_ids),
            severity=severity,
            seller_id=seller_id,
            detected_at=datetime.utcnow(),
        )

    @staticmethod
    def _cluster_severity(reviews: List[Review]) -> RiskLevel:
        if len(reviews) >= 10:
            return RiskLevel.ALTO
        elif len(reviews) >= 5:
            return RiskLevel.MEDIO
        return RiskLevel.BAJO

    @staticmethod
    def _find_burst(reviews: List[Review], window_minutes: int) -> List[Review]:
        """Retorna el subconjunto más grande dentro de la ventana de tiempo."""
        best: List[Review] = []
        window = timedelta(minutes=window_minutes)
        for i, start in enumerate(reviews):
            burst = [r for r in reviews[i:] if r.date - start.date <= window]
            if len(burst) > len(best):
                best = burst
        return best

    @staticmethod
    def _connected_components(
        adjacency: Dict[int, set], all_nodes: set
    ) -> List[set]:
        """BFS para encontrar componentes conexas en el grafo de similitud."""
        visited: set = set()
        components: List[set] = []
        for node in all_nodes:
            if node in visited:
                continue
            component: set = set()
            queue = [node]
            while queue:
                current = queue.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                queue.extend(adjacency.get(current, set()) - visited)
            if len(component) > 1:  # ignorar nodos aislados
                components.append(component)
        return components

    @staticmethod
    def _deduplicate(campaigns: List[FraudCampaign]) -> List[FraudCampaign]:
        """Elimina campañas que son subconjuntos de otra."""
        unique: List[FraudCampaign] = []
        sets = [set(c.review_ids) for c in campaigns]
        for i, camp in enumerate(campaigns):
            is_subset = any(
                sets[i] < sets[j]
                for j in range(len(campaigns)) if j != i
            )
            if not is_subset:
                unique.append(camp)
        return unique
