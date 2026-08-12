from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from . import models
from .config import settings
from .database import engine
from .rate_limit import limiter
from .routers import (
    accounts,
    admin,
    alerts,
    analysis,
    auth,
    banks,
    budgets,
    categories,
    categorization_rules,
    debtors,
    fixed_expenses,
    loans,
    net_worth,
    push,
    savings_goals,
    subscriptions,
    transactions,
)
from .services.enable_banking import EnableBankingClient

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, send_default_pii=False, traces_sample_rate=0.1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Solo crea tablas que falten (no altera las existentes): util para dev/tests
    # locales con base de datos nueva. Las migraciones reales sobre datos ya
    # existentes (anadir columnas, constraints) las gestiona Alembic.
    models.Base.metadata.create_all(bind=engine)

    app.state.eb_client = EnableBankingClient()
    try:
        yield
    finally:
        await app.state.eb_client.aclose()


app = FastAPI(title="Finanzas API", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
app.include_router(admin.router)
app.include_router(push.router)
app.include_router(subscriptions.router)
app.include_router(net_worth.router)
app.include_router(categorization_rules.router)
app.include_router(savings_goals.router)
app.include_router(fixed_expenses.router)
app.include_router(loans.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
