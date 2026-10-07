from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.models.database import Base, engine
from app.api.leads import router as leads_router
from app.api.webhooks import router as webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables when the application starts.
    Base.metadata.create_all(bind=engine)

    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered lead recovery backend for identifying "
        "high-intent and inactive leads."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(leads_router)
app.include_router(webhooks_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
    }
