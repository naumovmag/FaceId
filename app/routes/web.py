from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import structlog
from pathlib import Path

from app.config.database import get_db
from app.services.person_service import person_service
from app.config.settings import settings

logger = structlog.get_logger()

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """Главная страница - редирект на страницу идентификации"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Face Recognition System",
        "page": "index"
    })


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, db: Session = Depends(get_db)):
    """Страница загрузки фотографий"""
    try:
        # Получаем список всех людей для выбора
        persons = person_service.get_all_persons(db, limit=1000)

        return templates.TemplateResponse("upload.html", {
            "request": request,
            "title": "Загрузка фотографий",
            "persons": persons,
            "page": "upload"
        })
    except Exception as e:
        logger.error("Failed to load upload page", error=str(e))
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "title": "Загрузка фотографий",
            "persons": [],
            "error": "Не удалось загрузить список людей",
            "page": "upload"
        })


@router.get("/identify", response_class=HTMLResponse)
async def identify_page(request: Request, db: Session = Depends(get_db)):
    """Страница идентификации"""
    try:
        persons = person_service.get_all_persons(db, limit=1000)
        # Convert Pydantic models to simple dicts for JSON serialization in template
        persons = [{"id": p.id, "name": p.name} for p in persons]
    except Exception as e:
        logger.error("Failed to load persons for identify page", error=str(e))
        persons = []

    return templates.TemplateResponse("identify.html", {
        "request": request,
        "title": "Идентификация лица",
        "page": "identify",
        "persons": persons
    })


@router.get("/persons", response_class=HTMLResponse)
async def persons_list_page(
        request: Request,
        page: int = 1,
        db: Session = Depends(get_db)
):
    """Страница списка всех людей"""
    try:
        # Параметры пагинации
        page = max(page, 1)
        per_page = 20
        offset = (page - 1) * per_page

        persons = person_service.get_all_persons(db, limit=per_page + 1, offset=offset)

        # Проверяем есть ли следующая страница
        has_next = len(persons) > per_page
        if has_next:
            persons = persons[:per_page]

        has_prev = page > 1

        # Получаем статистику для каждого человека
        persons_with_stats = []
        for person in persons:
            stats = person_service.get_person_stats(db, person.id)
            persons_with_stats.append({
                'person': person,
                'stats': stats
            })

        return templates.TemplateResponse("persons_list.html", {
            "request": request,
            "title": "Список людей",
            "persons": persons_with_stats,
            "pagination": {
                'page': page,
                'has_prev': has_prev,
                'has_next': has_next,
                'prev_page': page - 1 if has_prev else None,
                'next_page': page + 1 if has_next else None
            },
            "page": "persons_list"
        })

    except Exception as e:
        logger.error("Failed to load persons list page", error=str(e))
        return templates.TemplateResponse("persons_list.html", {
            "request": request,
            "title": "Список людей",
            "persons": [],
            "error": "Не удалось загрузить список людей",
            "page": "persons_list"
        })


@router.get("/persons/{person_id}", response_class=HTMLResponse)
async def person_detail_page(
        request: Request,
        person_id: int,
        db: Session = Depends(get_db)
):
    """Страница детальной информации о человеке"""
    try:
        person = person_service.get_person_with_photos(db, person_id)
        if not person:
            return templates.TemplateResponse("person_detail.html", {
                "request": request,
                "title": "Человек не найден",
                "error": "Человек с указанным ID не найден",
                "page": "person_detail",
                "person": None
            })

        stats = person_service.get_person_stats(db, person_id)

        return templates.TemplateResponse("person_detail.html", {
            "request": request,
            "title": f"Информация о {person.name}",
            "person": person,
            "stats": stats,
            "page": "person_detail"
        })

    except ValueError:
        return templates.TemplateResponse("person_detail.html", {
            "request": request,
            "title": "Ошибка",
            "error": "Некорректный ID человека",
            "page": "person_detail",
            "person": None
        })
    except Exception as e:
        logger.error("Failed to load person detail page", error=str(e))
        return templates.TemplateResponse("person_detail.html", {
            "request": request,
            "title": "Ошибка",
            "error": "Не удалось загрузить информацию о человеке",
            "page": "person_detail",
            "person": None
        })


@router.get("/training", response_class=HTMLResponse)
async def training_page(request: Request, db: Session = Depends(get_db)):
    """Страница управления обучением"""
    try:
        # Импортируем модели локально, чтобы избежать проблем с импортом
        from app.models.database import Person as PersonDB, Photo as PhotoDB

        # Получаем статистику системы
        total_persons = db.query(PersonDB).count()
        active_photos = db.query(PhotoDB).filter(PhotoDB.is_active == True).count()
        inactive_photos = db.query(PhotoDB).filter(PhotoDB.is_active == False).count()

        # Средняя уверенность
        avg_confidence_result = db.query(PhotoDB.confidence).filter(
            PhotoDB.is_active == True
        ).all()

        avg_confidence = 0.0
        if avg_confidence_result:
            confidences = [r[0] for r in avg_confidence_result if r[0] is not None]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)

        # Количество людей с фотографиями
        persons_with_photos = db.query(PhotoDB.person_id).filter(
            PhotoDB.is_active == True
        ).distinct().count()

        # Получаем последние добавленные фотографии
        recent_photos_query = db.query(PhotoDB, PersonDB.name).join(
            PersonDB, PhotoDB.person_id == PersonDB.id
        ).filter(
            PhotoDB.is_active == True
        ).order_by(PhotoDB.created_at.desc()).limit(10).all()

        recent_photos = []
        for photo, person_name in recent_photos_query:
            recent_photos.append({
                'id': photo.id,
                'filename': photo.filename,
                'confidence': photo.confidence,
                'created_at': photo.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'person_name': person_name
            })

        return templates.TemplateResponse("training.html", {
            "request": request,
            "title": "Управление обучением",
            "stats": {
                'total_persons': total_persons,
                'active_photos': active_photos,
                'inactive_photos': inactive_photos,
                'avg_confidence': avg_confidence,
                'persons_with_photos': persons_with_photos
            },
            "recent_photos": recent_photos,
            "page": "training"
        })
    except Exception as e:
        logger.error("Failed to load training page", error=str(e))
        return templates.TemplateResponse("training.html", {
            "request": request,
            "title": "Управление обучением",
            "error": "Не удалось загрузить данные",
            "page": "training"
        })


@router.get("/results", response_class=HTMLResponse)
async def results_page(
        request: Request,
        person_id: int = None,
        person_name: str = "Неизвестно",
        similarity: float = 0.0,
        confidence: float = 0.0,
        is_match: bool = False,
        db: Session = Depends(get_db)
):
    """Страница результатов идентификации"""
    result_data = None
    if person_id:
        try:
            # Получаем дополнительную информацию о найденном человеке
            person = person_service.get_person_with_photos(db, person_id)
            if person:
                stats = person_service.get_person_stats(db, person_id)
                result_data = {
                    'person': person,
                    'stats': stats,
                    'similarity': similarity,
                    'confidence': confidence,
                    'is_match': is_match
                }
        except Exception as e:
            logger.error("Failed to load person data for results", error=str(e))

    return templates.TemplateResponse("results.html", {
        "request": request,
        "title": "Результаты идентификации",
        "result": result_data,
        "is_match": is_match,
        "similarity": similarity,
        "confidence": confidence,
        "person_name": person_name,
        "page": "results"
    })