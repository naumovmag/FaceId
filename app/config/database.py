from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import structlog

from .settings import settings

logger = structlog.get_logger()

# Создание движка базы данных
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug
)

# Создание сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Получить сессию базы данных"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database session error", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Создать все таблицы"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def drop_tables():
    """Удалить все таблицы (для разработки)"""
    Base.metadata.drop_all(bind=engine)
    logger.info("Database tables dropped")