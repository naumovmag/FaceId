from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import structlog
from contextlib import asynccontextmanager

from app.config.database import create_tables
from app.config.settings import settings
from app.services.face_service import face_service
from app.routes import api, web, auth, admin

# Настройка логирования
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info("Starting Face Recognition System")

    try:
        # Создаем таблицы БД
        create_tables()
        logger.info("Database tables created/verified")

        # Инициализируем сервис распознавания лиц
        face_service.initialize()
        logger.info("Face recognition service initialized")

    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down Face Recognition System")


def create_app() -> FastAPI:
    """Создание и настройка FastAPI приложения"""

    app = FastAPI(
        title="Face Recognition System",
        description="Система распознавания лиц с использованием InsightFace",
        version="1.0.0",
        debug=settings.debug,
        lifespan=lifespan
    )

    # Сессии
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

    # Подключение маршрутов
    app.include_router(api.router)
    app.include_router(web.router)
    app.include_router(auth.router)
    app.include_router(admin.router)

    # Статические файлы
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.mount("/uploads", StaticFiles(directory=settings.upload_path), name="uploads")

    return app


# Создаем экземпляр приложения
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
