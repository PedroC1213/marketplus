from marketplus_ai.detector.fraud_detector import FraudDetector
from marketplus_ai.models.schemas import Review, ReviewMetadata
from datetime import datetime


detector = FraudDetector()


def analyze_review(product, seller_id, rating, text):
    review = Review(
        id=0,
        product=product,
        product_id=product,
        seller_id=seller_id,
        rating=rating,
        text=text,
        user="api_user",
        metadata=ReviewMetadata(
            ip="127.0.0.1",
            device="web",
            user_id="api_user",
            date=datetime.utcnow(),
            previous_reviews=0,
            account_age_days=30,
        ),
        date=datetime.utcnow(),
    )

    result = detector.analyze(review)

    return {
        "fraud_score": result.score,
        "risk_level": result.risk_level.value,
    }
