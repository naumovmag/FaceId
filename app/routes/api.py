from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog

from app.config.database import get_db
from app.models.person import (
    Person, PersonCreate, PersonUpdate, PersonWithPhotos,
    IdentificationResult, PersonStats
)
from app.services.person_service import person_service
from app.services.face_service import face_service
from app.services.file_service import file_service
from app.utils.validators import (
    validate_upload_request, validate_identification_request,
    PersonValidator, FaceRecognitionValidator
)
from app.utils.exceptions import (
    FileValidationError, FileStorageError, FaceDetectionError,
    PersonNotFoundError, ValidationError
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["api"])


async def handle_api_error(e: Exception) -> HTTPException:
    """Обработчик ошибок API"""
    if isinstance(e, (FileValidationError, ValidationError)):
        return HTTPException(status_code=400, detail={
            'error': str(e),
            'error_type': 'validation_error'
        })

    elif isinstance(e, PersonNotFoundError):
        return HTTPException(status_code=404, detail={
            'error': str(e),
            'error_type': 'not_found'
        })

    elif isinstance(e, (FileStorageError, FaceDetectionError)):
        return HTTPException(status_code=422, detail={
            'error': str(e),
            'error_type': 'processing_error'
        })

    else:
        logger.error("Unexpected API error", error=str(e), error_type=type(e).__name__)
        return HTTPException(status_code=500, detail={
            'error': 'Внутренняя ошибка сервера',
            'error_type': 'internal_error'
        })


@router.post("/persons", response_model=Person)
async def create_person(person_data: PersonCreate, db: Session = Depends(get_db)):
    """Создать нового человека"""
    try:
        # Валидация имени
        validation_result = PersonValidator.validate_person_name(person_data.name)
        if not validation_result['is_valid']:
            raise ValidationError('; '.join(validation_result['errors']))

        person = person_service.create_person(db, person_data)
        return person

    except Exception as e:
        raise await handle_api_error(e)


@router.get("/persons", response_model=List[Person])
async def get_all_persons(
        limit: int = 50,
        offset: int = 0,
        db: Session = Depends(get_db)
):
    """Получить список всех людей"""
    try:
        limit = min(max(limit, 1), 100)  # Ограничиваем от 1 до 100
        offset = max(offset, 0)

        persons = person_service.get_all_persons(db, limit, offset)
        return persons

    except Exception as e:
        raise await handle_api_error(e)


@router.get("/persons/{person_id}", response_model=PersonWithPhotos)
async def get_person(person_id: int, db: Session = Depends(get_db)):
    """Получить информацию о человеке"""
    try:
        person = person_service.get_person_with_photos(db, person_id)
        if not person:
            raise PersonNotFoundError(f'Человек с ID {person_id} не найден')

        return person

    except Exception as e:
        raise await handle_api_error(e)


@router.put("/persons/{person_id}", response_model=Person)
async def update_person(
        person_id: int,
        person_data: PersonUpdate,
        db: Session = Depends(get_db)
):
    """Обновить информацию о человеке"""
    try:
        # Валидация имени (если передано)
        if person_data.name is not None:
            validation_result = PersonValidator.validate_person_name(person_data.name)
            if not validation_result['is_valid']:
                raise ValidationError('; '.join(validation_result['errors']))

        person = person_service.update_person(db, person_id, person_data)
        if not person:
            raise PersonNotFoundError(f'Человек с ID {person_id} не найден')

        return person

    except Exception as e:
        raise await handle_api_error(e)


@router.delete("/persons/{person_id}")
async def delete_person(person_id: int, db: Session = Depends(get_db)):
    """Удалить человека"""
    try:
        deleted = person_service.delete_person(db, person_id)
        if not deleted:
            raise PersonNotFoundError(f'Человек с ID {person_id} не найден')

        return {"message": "Человек успешно удален"}

    except Exception as e:
        raise await handle_api_error(e)


@router.post("/persons/{person_id}/photos")
async def upload_photo(
        person_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """Загрузить фотографию для человека"""
    try:
        # Проверяем существование человека
        person = person_service.get_person(db, person_id)
        if not person:
            raise PersonNotFoundError(f'Человек с ID {person_id} не найден')

        # Читаем файл
        file_data = await file.read()

        # Валидация запроса
        validation_result = validate_upload_request(file.filename, len(file_data), person_id)
        if not validation_result['is_valid']:
            raise ValidationError('; '.join(validation_result['errors']))

        # Сохраняем файл
        file_info = await file_service.save_uploaded_file(
            file_data, file.filename, person_id=person_id
        )

        # Получаем эмбеддинг лица
        embedding, confidence = face_service.get_face_embedding(file_info['file_path'])

        # Сохраняем фотографию в БД
        photo = person_service.add_photo_to_person(
            db=db,
            person_id=person_id,
            filename=file_info['filename'],
            file_path=file_info['relative_path'],
            embedding_vector=embedding.tolist(),
            confidence=confidence
        )

        if not photo:
            # Удаляем файл если не удалось сохранить в БД
            await file_service.delete_file(file_info['file_path'])
            raise FileStorageError('Не удалось сохранить фотографию в базе данных')

        return {
            "photo_id": photo.id,
            "filename": photo.filename,
            "confidence": photo.confidence,
            "person_id": photo.person_id,
            "created_at": photo.created_at
        }

    except Exception as e:
        raise await handle_api_error(e)


@router.delete("/photos/{photo_id}")
async def deactivate_photo(photo_id: int, db: Session = Depends(get_db)):
    """Деактивировать фотографию"""
    try:
        deactivated = person_service.deactivate_photo(db, photo_id)
        if not deactivated:
            raise HTTPException(status_code=404, detail="Фотография не найдена")

        return {"message": "Фотография деактивирована"}

    except Exception as e:
        raise await handle_api_error(e)


@router.post("/identify", response_model=IdentificationResult)
async def identify_person(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Идентифицировать человека по фотографии"""
    try:
        # Читаем файл
        file_data = await file.read()

        # Валидация запроса
        validation_result = validate_upload_request(file.filename, len(file_data))
        if not validation_result['is_valid']:
            raise ValidationError('; '.join(validation_result['errors']))

        # Сохраняем временный файл
        file_info = await file_service.save_uploaded_file(
            file_data, file.filename, temp=True
        )

        try:
            # Валидация изображения для идентификации
            image_validation = validate_identification_request(file_info['file_path'])
            if not image_validation['is_valid']:
                raise ValidationError('; '.join(image_validation['errors']))

            # Выполняем идентификацию
            result = person_service.identify_person(db, file_info['file_path'])
            return result

        finally:
            # Удаляем временный файл
            await file_service.delete_file(file_info['file_path'])

    except Exception as e:
        raise await handle_api_error(e)


@router.get("/persons/{person_id}/stats", response_model=PersonStats)
async def get_person_stats(person_id: int, db: Session = Depends(get_db)):
    """Получить статистику по человеку"""
    try:
        # Проверяем существование человека
        person = person_service.get_person(db, person_id)
        if not person:
            raise PersonNotFoundError(f'Человек с ID {person_id} не найден')

        stats = person_service.get_person_stats(db, person_id)
        return PersonStats(**stats)

    except Exception as e:
        raise await handle_api_error(e)


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Проверка состояния системы"""
    try:
        # Проверяем инициализацию Face ID сервиса
        if not face_service._initialized:
            face_service.initialize()

        # Проверяем подключение к БД
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "services": {
                "face_recognition": "ok",
                "database": "ok"
            }
        }

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail={
            "status": "unhealthy",
            "error": str(e)
        })


@router.get("/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """Получить статистику системы"""
    try:
        from app.models.database import PersonDB, PhotoDB

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

        return {
            "total_persons": total_persons,
            "active_photos": active_photos,
            "inactive_photos": inactive_photos,
            "avg_confidence": avg_confidence,
            "face_recognition_threshold": face_service.settings.face_recognition_threshold
        }

    except Exception as e:
        raise await handle_api_error(e)