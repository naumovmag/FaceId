import insightface
import cv2
import numpy as np
from typing import Optional, List, Tuple
import structlog
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor

from app.config.settings import settings
from app.utils.exceptions import ModelInitializationError, FaceDetectionError

logger = structlog.get_logger()


class FaceService:
    """Сервис для работы с распознаванием лиц"""

    _instance: Optional['FaceService'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'FaceService':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self.face_app = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._initialized = False

    def initialize(self) -> None:
        """Инициализация модели (синхронная версия по примеру)"""
        if self._initialized:
            return

        try:
            # Создаем директорию для кэша моделей
            Path(settings.models_cache_path).mkdir(parents=True, exist_ok=True)

            logger.info("Starting InsightFace initialization...")

            # Инициализация по рабочему примеру
            self.face_app = insightface.app.FaceAnalysis(
                name='buffalo_l',
                providers=['CPUExecutionProvider']
            )
            self.face_app.prepare(ctx_id=0, det_size=(640, 640))

            self._initialized = True
            logger.info("FaceService initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize FaceService", error=str(e))
            raise ModelInitializationError(f"Не удалось инициализировать модель: {str(e)}")

    def get_face_embedding(self, image_path: str) -> Tuple[np.ndarray, float]:
        """
        Получить эмбеддинг лица из изображения

        Args:
            image_path: Путь к изображению

        Returns:
            Tuple[embedding, confidence]: Эмбеддинг и уверенность детекции
        """
        if not self._initialized:
            self.initialize()

        if not Path(image_path).exists():
            raise FaceDetectionError(f'Файл не найден: {image_path}')

        img = cv2.imread(image_path)
        if img is None:
            raise FaceDetectionError(f'Не удалось загрузить изображение: {image_path}')

        # Проверяем размер изображения
        height, width = img.shape[:2]
        if height < 50 or width < 50:
            raise FaceDetectionError('Изображение слишком маленькое (минимум 50x50 пикселей)')

        faces = self.face_app.get(img)
        logger.debug(f'Найдено лиц: {len(faces)}', image_path=image_path)

        if not faces:
            # Сохраняем изображение для отладки
            debug_path = Path(settings.upload_path) / 'debug' / 'no_faces_debug.jpg'
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(debug_path), img)
            raise FaceDetectionError('Лицо не найдено на изображении')

        if len(faces) > 1:
            logger.warning(f'Найдено {len(faces)} лиц, используется первое', image_path=image_path)

        face = faces[0]
        confidence = getattr(face, 'det_score', 0.9)

        return face.embedding, float(confidence)

    def compare_embeddings(
            self,
            embedding1: np.ndarray,
            embedding2: np.ndarray,
            threshold: Optional[float] = None
    ) -> Tuple[bool, float]:
        """Сравнить два эмбеддинга"""
        if threshold is None:
            threshold = settings.face_recognition_threshold

        # Косинусное сходство по рабочему примеру
        similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )

        is_same = float(similarity) > threshold
        return is_same, float(similarity)

    def find_best_match(
            self,
            target_embedding: np.ndarray,
            candidate_embeddings: List[Tuple[int, np.ndarray]],
            threshold: Optional[float] = None
    ) -> Optional[Tuple[int, float]]:
        """Найти наиболее похожий эмбеддинг"""
        if not candidate_embeddings:
            return None

        if threshold is None:
            threshold = settings.face_recognition_threshold

        best_match = None
        best_similarity = 0.0

        logger.info("Comparing embeddings",
                    target_size=len(target_embedding),
                    candidates_count=len(candidate_embeddings),
                    threshold=threshold)

        for candidate_id, candidate_embedding in candidate_embeddings:
            try:
                is_match, similarity = self.compare_embeddings(
                    target_embedding,
                    candidate_embedding,
                    threshold
                )

                logger.debug("Comparison result",
                             candidate_id=candidate_id,
                             similarity=similarity,
                             is_match=is_match)

                if is_match and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = (candidate_id, similarity)

            except Exception as e:
                logger.error("Error comparing embeddings",
                             candidate_id=candidate_id,
                             error=str(e))
                continue

        if best_match:
            logger.info("Best match found",
                        photo_id=best_match[0],
                        similarity=best_match[1])
        else:
            logger.info("No match found above threshold", threshold=threshold)

        return best_match


# Глобальный экземпляр сервиса
face_service = FaceService()