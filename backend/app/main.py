from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .config import settings
from .database import SessionLocal, engine
from .default_categories import seed_if_needed
from .routers import accounts, alerts, analysis, auth, banks, budgets, categories, debtors, transactions
from .services.enable_banking import EnableBankingClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_needed(db)
    finally:
        db.close()

    app.state.eb_client = EnableBankingClient()
    try:
        yield
    finally:
        await app.state.eb_client.aclose()


app = FastAPI(title="Finanzas API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(banks.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(alerts.router)
app.include_router(analysis.router)
app.include_router(debtors.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
