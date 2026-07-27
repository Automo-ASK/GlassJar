from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core.errors import DomainError
from app.core.rate_limit import limiter
from app.database import Base, engine

import app.models  # noqa: F401  (register all tables on Base.metadata)

from app.routers.assistant import router as assistant_router
from app.routers.auth import router as auth_router
from app.routers.collections import router as collections_router
from app.routers.communities import router as communities_router
from app.routers.expenses import router as expenses_router
from app.routers.meta import router as meta_router
from app.routers.payments import router as payments_router
from app.routers.public import router as public_router
from app.routers.reports import router as reports_router
from app.routers.users import router as users_router
from app.routers.webhooks import router as webhooks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # SQLite (dev/tests) is created on the fly; Postgres schema is managed by
    # Alembic ("alembic upgrade head" runs before the server starts).
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

# Rate limiting: @limiter.limit decorators reference app.state.limiter, and
# RateLimitExceeded needs a handler to become a 429 instead of a 500.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Raised exceptions bypass CORSMiddleware, so a bare 500 would reach the
    # browser without CORS headers and be misreported as a CORS failure.
    headers = {}
    origin = request.headers.get("origin")
    if origin and origin in settings.cors_origins:
        headers["Access-Control-Allow-Origin"] = origin
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers,
    )


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(communities_router)
app.include_router(collections_router)
app.include_router(payments_router)
app.include_router(public_router)
app.include_router(webhooks_router)
app.include_router(expenses_router)
app.include_router(meta_router)
app.include_router(reports_router)
app.include_router(assistant_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name, "env": settings.env}
