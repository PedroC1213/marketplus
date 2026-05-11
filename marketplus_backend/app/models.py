from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(100), unique=True)
    password = Column(String(255))


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    product = Column(String(255))
    seller_id = Column(String(100))
    rating = Column(Integer)
    text = Column(Text)
    fraud_score = Column(Float)
    risk_level = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())
