from typing import Optional, Dict, Any


class FaceRecognitionBaseException(Exception):
    """Базовое исключение для системы распознавания лиц"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class FileValidationError(FaceRecognitionBaseException):
    """Ошибка валидации файла"""
    pass


class FileStorageError(FaceRecognitionBaseException):
    """Ошибка сохранения файла"""
    pass


class FaceDetectionError(FaceRecognitionBaseException):
    """Ошибка детекции лица"""
    pass


class PersonNotFoundError(FaceRecognitionBaseException):
    """Человек не найден"""
    pass


class PhotoNotFoundError(FaceRecognitionBaseException):
    """Фотография не найдена"""
    pass


class DatabaseError(FaceRecognitionBaseException):
    """Ошибка базы данных"""
    pass


class ModelInitializationError(FaceRecognitionBaseException):
    """Ошибка инициализации модели"""
    pass


class ValidationError(FaceRecognitionBaseException):
    """Ошибка валидации данных"""
    pass