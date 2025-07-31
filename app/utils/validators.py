import re
from typing import List, Optional, Dict, Any
from pathlib import Path
import mimetypes

from app.config.settings import settings


class FileValidator:
    """Валидатор для файлов"""

    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Валидация имени файла"""
        if not filename or len(filename.strip()) == 0:
            return False

        # Проверка на недопустимые символы
        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, filename):
            return False

        # Проверка длины
        if len(filename) > 255:
            return False

        return True

    @staticmethod
    def validate_file_extension(filename: str) -> bool:
        """Валидация расширения файла"""
        if not filename:
            return False

        extension = Path(filename).suffix.lower().lstrip('.')
        allowed_extensions = settings.get_allowed_extensions_list()
        return extension in allowed_extensions

    @staticmethod
    def validate_file_size(size: int) -> bool:
        """Валидация размера файла"""
        return 0 < size <= settings.max_upload_size

    @staticmethod
    def validate_mime_type(filename: str) -> bool:
        """Валидация MIME типа файла"""
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            return False

        allowed_mime_types = [
            'image/jpeg',
            'image/jpg',
            'image/png'
        ]

        return mime_type.lower() in allowed_mime_types

    @staticmethod
    def validate_image_dimensions(width: int, height: int) -> Dict[str, Any]:
        """Валидация размеров изображения"""
        result = {
            'is_valid': True,
            'errors': []
        }

        # Минимальные размеры
        if width < 50 or height < 50:
            result['is_valid'] = False
            result['errors'].append('Изображение слишком маленькое (минимум 50x50 пикселей)')

        # Максимальные размеры
        if width > 4000 or height > 4000:
            result['is_valid'] = False
            result['errors'].append('Изображение слишком большое (максимум 4000x4000 пикселей)')

        # Соотношение сторон
        if width > 0 and height > 0:
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > 5.0:
                result['errors'].append('Слишком большое соотношение сторон изображения')

        return result


class PersonValidator:
    """Валидатор для данных о людях"""

    @staticmethod
    def validate_person_name(name: str) -> Dict[str, Any]:
        """Валидация имени человека"""
        result = {
            'is_valid': True,
            'errors': []
        }

        if not name or len(name.strip()) == 0:
            result['is_valid'] = False
            result['errors'].append('Имя не может быть пустым')
            return result

        name = name.strip()

        # Проверка длины
        if len(name) < 2:
            result['is_valid'] = False
            result['errors'].append('Имя слишком короткое (минимум 2 символа)')

        if len(name) > 255:
            result['is_valid'] = False
            result['errors'].append('Имя слишком длинное (максимум 255 символов)')

        # Проверка на недопустимые символы
        if re.search(r'[<>"/\\|?*]', name):
            result['is_valid'] = False
            result['errors'].append('Имя содержит недопустимые символы')

        # Проверка на только пробелы и специальные символы
        if not re.search(r'[a-zA-Zа-яА-Я0-9]', name):
            result['is_valid'] = False
            result['errors'].append('Имя должно содержать буквы или цифры')

        return result

    @staticmethod
    def validate_person_id(person_id: Any) -> bool:
        """Валидация ID человека"""
        try:
            id_int = int(person_id)
            return id_int > 0
        except (ValueError, TypeError):
            return False


class FaceRecognitionValidator:
    """Валидатор для параметров распознавания лиц"""

    @staticmethod
    def validate_threshold(threshold: float) -> bool:
        """Валидация порога сходства"""
        return 0.0 <= threshold <= 1.0

    @staticmethod
    def validate_confidence(confidence: float) -> bool:
        """Валидация уверенности детекции"""
        return 0.0 <= confidence <= 1.0

    @staticmethod
    def validate_embedding_vector(embedding: List[float]) -> Dict[str, Any]:
        """Валидация вектора эмбеддинга"""
        result = {
            'is_valid': True,
            'errors': []
        }

        if not embedding:
            result['is_valid'] = False
            result['errors'].append('Вектор эмбеддинга пустой')
            return result

        # Проверка размерности (InsightFace buffalo_l = 512)
        expected_dim = 512
        if len(embedding) != expected_dim:
            result['is_valid'] = False
            result['errors'].append(
                f'Неверная размерность вектора. Ожидается: {expected_dim}, получено: {len(embedding)}'
            )

        # Проверка на валидные значения
        try:
            for i, val in enumerate(embedding):
                if not isinstance(val, (int, float)):
                    result['is_valid'] = False
                    result['errors'].append(f'Некорректное значение в позиции {i}: {val}')
                    break

                # Проверка на NaN и бесконечность
                if val != val or abs(val) == float('inf'):
                    result['is_valid'] = False
                    result['errors'].append(f'Некорректное значение в позиции {i}: {val}')
                    break

        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f'Ошибка при валидации вектора: {str(e)}')

        return result


def validate_upload_request(
    filename: Optional[str],
    file_size: Optional[int],
    person_id: Optional[int] = None
) -> Dict[str, Any]:
    """Комплексная валидация запроса на загрузку файла"""
    result = {
        'is_valid': True,
        'errors': []
    }

    # Валидация имени файла
    if not filename:
        result['is_valid'] = False
        result['errors'].append('Имя файла не указано')
    else:
        if not FileValidator.validate_filename(filename):
            result['is_valid'] = False
            result['errors'].append('Некорректное имя файла')

        if not FileValidator.validate_file_extension(filename):
            result['is_valid'] = False
            allowed_extensions = settings.get_allowed_extensions_list()
            result['errors'].append(
                f'Неподдерживаемое расширение файла. Разрешены: {", ".join(allowed_extensions)}'
            )

        if not FileValidator.validate_mime_type(filename):
            result['is_valid'] = False
            result['errors'].append('Неподдерживаемый тип файла')

    # Валидация размера файла
    if file_size is None:
        result['is_valid'] = False
        result['errors'].append('Размер файла не указан')
    elif not FileValidator.validate_file_size(file_size):
        max_size_mb = settings.max_upload_size / (1024 * 1024)
        result['is_valid'] = False
        result['errors'].append(f'Файл слишком большой. Максимальный размер: {max_size_mb:.1f} MB')

    # Валидация ID человека (если указан)
    if person_id is not None and not PersonValidator.validate_person_id(person_id):
        result['is_valid'] = False
        result['errors'].append('Некорректный ID человека')

    return result


def validate_identification_request(image_path: str) -> Dict[str, Any]:
    """Валидация запроса на идентификацию"""
    result = {
        'is_valid': True,
        'errors': []
    }

    if not image_path:
        result['is_valid'] = False
        result['errors'].append('Путь к изображению не указан')
        return result

    path = Path(image_path)

    if not path.exists():
        result['is_valid'] = False
        result['errors'].append('Файл изображения не найден')
        return result

    if not path.is_file():
        result['is_valid'] = False
        result['errors'].append('Указанный путь не является файлом')
        return result

    # Проверка расширения
    if not FileValidator.validate_file_extension(path.name):
        result['is_valid'] = False
        result['errors'].append('Неподдерживаемый формат изображения')

    return result