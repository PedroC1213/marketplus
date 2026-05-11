from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import reviews, dashboard

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MarketPlus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reviews.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"message": "MarketPlus Backend funcionando"}
