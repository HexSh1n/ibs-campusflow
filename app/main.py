from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.errors import Utf8JSONResponse, register_exception_handlers
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.bookings import router as bookings_router
from app.routers.rooms import router as rooms_router
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    seed_if_empty()
    yield


def create_app() -> FastAPI:
    """Собирает приложение FastAPI с роутерами, обработчиками ошибок и сидированием."""
    application = FastAPI(
        title="IBS CampusFlow API",
        version="1.0.0",
        default_response_class=Utf8JSONResponse,
        lifespan=lifespan,
    )
    register_exception_handlers(application)

    @application.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(auth_router)
    application.include_router(rooms_router)
    application.include_router(bookings_router)
    application.include_router(admin_router)
    return application


app = create_app()
