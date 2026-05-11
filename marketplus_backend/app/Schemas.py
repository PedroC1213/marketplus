from pydantic import BaseModel


class ReviewCreate(BaseModel):
    product: str
    seller_id: str
    rating: int
    text: str


class ReviewResponse(BaseModel):
    id: int
    fraud_score: float
    risk_level: str

    class Config:
        from_attributes = True
