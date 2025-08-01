from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
import structlog
import numpy as np
import pickle
from pathlib import Path
import shutil

from app.models.database import Person as PersonDB, Photo as PhotoDB
from app.models.person import Person, PersonCreate, PersonUpdate, PersonWithPhotos, Photo, IdentificationResult
from app.services.face_service import face_service
from app.config.settings import settings
from app.utils.exceptions import PersonNotFoundError, DatabaseError, FaceDetectionError

logger = structlog.get_logger()


class PersonService:
    """Сервис для работы с людьми и их фотографиями"""

    def create_person(self, db: Session, person_data: PersonCreate) -> Person:
        """Создать нового человека"""
        try:
            db_person = PersonDB(name=person_data.name)
            db.add(db_person)
            db.commit()
            db.refresh(db_person)

            logger.info("Person created", person_id=db_person.id, name=person_data.name)
            return Person.from_orm(db_person)

        except Exception as e:
            db.rollback()
            logger.error("Failed to create person", error=str(e))
            raise DatabaseError(f"Не удалось создать человека: {str(e)}")

    def get_person(self, db: Session, person_id: int) -> Optional[Person]:
        """Получить человека по ID"""
        db_person = db.query(PersonDB).filter(PersonDB.id == person_id).first()
        if db_person:
            return Person.from_orm(db_person)
        return None

    def get_person_with_photos(self, db: Session, person_id: int) -> Optional[PersonWithPhotos]:
        """Получить человека с его фотографиями"""
        db_person = db.query(PersonDB).filter(PersonDB.id == person_id).first()
        if not db_person:
            return None

        # Получаем активные фотографии
        active_photos = db.query(PhotoDB).filter(
            PhotoDB.person_id == person_id,
            PhotoDB.is_active == True
        ).order_by(PhotoDB.created_at.desc()).all()

        person_dict = {
            'id': db_person.id,
            'name': db_person.name,
            'created_at': db_person.created_at,
            'updated_at': db_person.updated_at,
            'photos': [Photo.from_orm(photo) for photo in active_photos]
        }

        return PersonWithPhotos(**person_dict)

    def get_all_persons(self, db: Session, limit: int = 100, offset: int = 0) -> List[Person]:
        """Получить список всех людей"""
        db_persons = db.query(PersonDB).order_by(
            PersonDB.created_at.desc()
        ).limit(limit).offset(offset).all()

        return [Person.from_orm(person) for person in db_persons]

    def update_person(self, db: Session, person_id: int, person_data: PersonUpdate) -> Optional[Person]:
        """Обновить данные человека"""
        try:
            db_person = db.query(PersonDB).filter(PersonDB.id == person_id).first()
            if not db_person:
                return None

            if person_data.name is not None:
                db_person.name = person_data.name

            db.commit()
            db.refresh(db_person)

            logger.info("Person updated", person_id=person_id, new_name=person_data.name)
            return Person.from_orm(db_person)

        except Exception as e:
            db.rollback()
            logger.error("Failed to update person", error=str(e))
            raise DatabaseError(f"Не удалось обновить человека: {str(e)}")

    def delete_person(self, db: Session, person_id: int) -> bool:
        """Удалить человека и все его фотографии"""
        try:
            db_person = db.query(PersonDB).filter(PersonDB.id == person_id).first()
            if not db_person:
                return False

            photos = db.query(PhotoDB).filter(PhotoDB.person_id == person_id).all()
            base_path = Path(settings.upload_path)

            for photo in photos:
                file_path = base_path / photo.file_path
                try:
                    if file_path.exists():
                        file_path.unlink()
                except Exception as e:
                    db.rollback()
                    logger.error(
                        "Failed to delete photo file",
                        error=str(e),
                        file_path=str(file_path),
                        photo_id=photo.id,
                    )
                    raise DatabaseError(f"Не удалось удалить файл фотографии: {str(e)}")

            try:
                shutil.rmtree(base_path / 'persons' / str(person_id), ignore_errors=True)
            except Exception as e:
                db.rollback()
                logger.error(
                    "Failed to delete person directory",
                    error=str(e),
                    person_id=person_id,
                )
                raise DatabaseError(f"Не удалось удалить каталог пользователя: {str(e)}")

            db.delete(db_person)
            db.commit()

            logger.info("Person deleted", person_id=person_id)
            return True

        except DatabaseError:
            raise
        except Exception as e:
            db.rollback()
            logger.error("Failed to delete person", error=str(e))
            raise DatabaseError(f"Не удалось удалить человека: {str(e)}")

    def add_photo_to_person(
            self,
            db: Session,
            person_id: int,
            filename: str,
            file_path: str,
            embedding_vector: List[float],
            confidence: float = 0.0
    ) -> Optional[Photo]:
        """Добавить фотографию к человеку"""
        # Проверяем валидность эмбеддинга до обращения к базе
        if not embedding_vector or len(embedding_vector) != 512:
            logger.error(
                "Invalid embedding vector",
                embedding_size=len(embedding_vector) if embedding_vector else 0,
                expected_size=512,
            )
            raise FaceDetectionError("Некорректный вектор эмбеддинга")

        try:
            # Конвертируем эмбеддинг в bytes для хранения в SQLite
            embedding_array = np.array(embedding_vector, dtype=np.float32)
            embedding_bytes = pickle.dumps(embedding_array)

            logger.info(
                "Saving photo with embedding",
                person_id=person_id,
                filename=filename,
                embedding_size=len(embedding_vector),
                confidence=confidence,
            )

            db_photo = PhotoDB(
                person_id=person_id,
                filename=filename,
                file_path=file_path,
                embedding_vector=embedding_bytes,
                confidence=confidence,
            )

            db.add(db_photo)
            db.commit()
            db.refresh(db_photo)

            # Проверяем, что данные сохранились
            saved_embedding = pickle.loads(db_photo.embedding_vector)
            logger.info(
                "Photo saved successfully",
                person_id=person_id,
                photo_id=db_photo.id,
                filename=filename,
                saved_embedding_size=len(saved_embedding),
            )

            return Photo.from_orm(db_photo)

        except Exception as e:
            db.rollback()
            logger.error("Failed to add photo", error=str(e), person_id=person_id)
            raise DatabaseError(f"Не удалось добавить фотографию: {str(e)}")

    def delete_photo(self, db: Session, photo_id: int) -> Optional[str]:
        """Удалить фотографию из базы данных и вернуть путь к файлу"""
        try:
            db_photo = db.query(PhotoDB).filter(PhotoDB.id == photo_id).first()
            if not db_photo:
                return None

            file_path = db_photo.file_path
            db.delete(db_photo)
            db.commit()

            logger.info("Photo deleted", photo_id=photo_id)
            return file_path

        except Exception as e:
            db.rollback()
            logger.error("Failed to delete photo", error=str(e))
            raise DatabaseError(f"Не удалось удалить фотографию: {str(e)}")

    def get_all_active_embeddings(self, db: Session) -> List[Dict[str, Any]]:
        """Получить все активные эмбеддинги для поиска"""
        try:
            active_photos = db.query(PhotoDB, PersonDB.name).join(
                PersonDB, PhotoDB.person_id == PersonDB.id
            ).filter(
                PhotoDB.is_active == True,
                PhotoDB.embedding_vector.isnot(None)
            ).order_by(PhotoDB.created_at.desc()).all()

            embeddings = []
            for photo, person_name in active_photos:
                try:
                    # Десериализуем эмбеддинг из bytes
                    embedding = pickle.loads(photo.embedding_vector)

                    # Проверяем валидность эмбеддинга
                    if embedding is None or len(embedding) != 512:
                        logger.warning("Invalid embedding found",
                                       photo_id=photo.id,
                                       embedding_size=len(embedding) if embedding is not None else 0)
                        continue

                    embeddings.append({
                        'photo_id': photo.id,
                        'person_id': photo.person_id,
                        'person_name': person_name,
                        'embedding_vector': embedding,
                        'confidence': photo.confidence
                    })

                    logger.debug("Loaded embedding",
                                 photo_id=photo.id,
                                 person_name=person_name,
                                 embedding_size=len(embedding))

                except Exception as e:
                    logger.error("Failed to deserialize embedding",
                                 photo_id=photo.id,
                                 error=str(e))
                    continue

            logger.info("Loaded embeddings for identification",
                        total_embeddings=len(embeddings))
            return embeddings

        except Exception as e:
            logger.error("Failed to get active embeddings", error=str(e))
            raise DatabaseError(f"Не удалось получить эмбеддинги: {str(e)}")

    def identify_person(self, db: Session, image_path: str) -> Tuple[IdentificationResult, np.ndarray]:
        """Идентифицировать человека по фотографии и вернуть эмбеддинг"""
        from app.utils.exceptions import FaceDetectionError
        try:
            logger.info("Starting person identification", image_path=image_path)

            # Получаем эмбеддинг из изображения
            try:
                target_embedding, detection_confidence = face_service.get_face_embedding(image_path)
            except FaceDetectionError as e:
                logger.error("Face detection failed", error=str(e), image_path=image_path)
                raise
            except Exception as e:
                logger.error("Failed to get face embedding", error=str(e), image_path=image_path)
                raise

            logger.info("Face embedding extracted",
                        confidence=detection_confidence,
                        embedding_size=len(target_embedding))

            # Получаем все активные эмбеддинги
            all_embeddings = self.get_all_active_embeddings(db)

            if not all_embeddings:
                logger.warning("No embeddings found in database")
                return IdentificationResult(
                    confidence=detection_confidence,
                    similarity=0.0,
                    is_match=False
                ), target_embedding

            logger.info("Found embeddings in database", count=len(all_embeddings))

            # Подготавливаем кандидатов для сравнения
            candidates = [
                (row['photo_id'], row['embedding_vector'])
                for row in all_embeddings
            ]

            # Находим лучшее совпадение
            best_match = face_service.find_best_match(target_embedding, candidates)

            if not best_match:
                logger.info("No match found above threshold")
                return IdentificationResult(
                    confidence=detection_confidence,
                    similarity=0.0,
                    is_match=False
                ), target_embedding

            # Получаем информацию о найденном человеке
            best_photo_id, similarity = best_match
            matched_row = next(
                (row for row in all_embeddings if row['photo_id'] == best_photo_id),
                None
            )

            if matched_row:
                logger.info("Person identified",
                            person_id=matched_row['person_id'],
                            person_name=matched_row['person_name'],
                            similarity=similarity,
                            threshold=settings.face_recognition_threshold)

                return IdentificationResult(
                    person_id=matched_row['person_id'],
                    person_name=matched_row['person_name'],
                    confidence=detection_confidence,
                    similarity=similarity,
                    is_match=True,
                    photo_id=best_photo_id
                ), target_embedding

            return IdentificationResult(
                confidence=detection_confidence,
                similarity=similarity,
                is_match=False
            ), target_embedding

        except FaceDetectionError:
            raise
        except Exception as e:
            logger.error("Failed to identify person", error=str(e), image_path=image_path)
            return IdentificationResult(
                confidence=0.0,
                similarity=0.0,
                is_match=False
            ), np.array([])

    def get_person_stats(self, db: Session, person_id: int) -> Dict[str, Any]:
        """Получить статистику по человеку"""
        try:
            photos = db.query(PhotoDB).filter(PhotoDB.person_id == person_id).all()

            active_photos = [p for p in photos if p.is_active]
            total_photos = len(photos)
            active_count = len(active_photos)

            avg_confidence = 0.0
            last_photo_date = None
            preview_photo = None

            if active_photos:
                avg_confidence = sum(p.confidence for p in active_photos) / active_count
                last_photo_date = max(p.created_at for p in active_photos)
                first_photo = min(active_photos, key=lambda p: p.created_at)
                preview_photo = first_photo.file_path

            return {
                'total_photos': total_photos,
                'active_photos': active_count,
                'avg_confidence': avg_confidence,
                'last_photo_date': last_photo_date,
                'preview_photo': preview_photo
            }

        except Exception as e:
            logger.error("Failed to get person stats", error=str(e))
            return {
                'total_photos': 0,
                'active_photos': 0,
                'avg_confidence': 0.0,
                'last_photo_date': None,
                'preview_photo': None
            }


# Глобальный экземпляр сервиса
person_service = PersonService()
