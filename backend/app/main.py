"""GoldProof FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 - ensure all 14 tables are registered on Base.metadata
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import analytics, assistant, auth, ocr, passports, sync, transactions
from app.services.seed import seed_demo_data


def init_db_and_seed() -> None:
    """Create database tables and optionally seed idempotent [DEMO] records."""
    Base.metadata.create_all(bind=engine)
    if get_settings().DEMO_MODE:
        db = SessionLocal()
        try:
            seed_demo_data(db)
        finally:
            db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db_and_seed()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "GoldProof — AI-powered gold exchange intelligence and verifiable Digital Gold Passport API."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(transactions.router)
    app.include_router(passports.router)
    app.include_router(assistant.router)
    app.include_router(ocr.router)
    app.include_router(analytics.router)
    app.include_router(sync.router)

    @app.get("/health", tags=["System"])
    def health_check():
        return {
            "status": "ok",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "demo_mode": settings.DEMO_MODE,
        }

    return app


app = create_app()
