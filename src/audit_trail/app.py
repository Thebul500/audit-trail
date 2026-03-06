"""audit-trail — FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .routes.auth import router as auth_router
from .routes.events import router as events_router
from .routes.health import router as health_router
from .routes.retention import router as retention_router
from .routes.webhooks import router as webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="audit-trail",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(events_router)
    app.include_router(retention_router)
    app.include_router(webhooks_router)
    return app


app = create_app()
