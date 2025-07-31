import os
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
import structlog
from datetime import datetime
import hashlib
import uuid
from PIL import Image

from app.config.settings import settings
from app.utils.exceptions import FileValidationError, FileStorageError

logger = structlog.get_logger()


class FileService:
    """Сервис для работы с файлами"""

    def __init__(self):
        self.upload_path = Path(settings.upload_path)
        self.max_file_size = settings.max_upload_size
        self.allowed_extensions = settings.get_allowed_extensions_list()

        # Создаем необходимые директории
        self._create_directories()

    def _create_directories(self):
        """Создать необходимые директории"""
        directories = [
            self.upload_path,
            self.upload_path / 'temp',
            self.upload_path / 'persons',
            self.upload_path / 'debug'
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def validate_file_extension(self, filename: str) -> bool:
        """Проверить расширение файла"""
        if not filename:
            return False

        extension = Path(filename).suffix.lower().lstrip('.')
        return extension in self.allowed_extensions

    def validate_file_size(self, file_size: int) -> bool:
        """Проверить размер файла"""
        return 0 < file_size <= self.max_file_size

    async def validate_image_content(self, file_path: str) -> Dict[str, Any]:
        """Валидация содержимого изображения"""
        try:
            with Image.open(file_path) as img:
                info = {
                    'is_valid': True,
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'errors': []
                }

                # Проверки
                if img.width < 50 or img.height < 50:
                    info['errors'].append('Изображение слишком маленькое (минимум 50x50)')
                    info['is_valid'] = False

                if img.width > 4000 or img.height > 4000:
                    info['errors'].append('Изображение слишком большое (максимум 4000x4000)')
                    info['is_valid'] = False

                if img.format not in ['JPEG', 'PNG']:
                    info['errors'].append('Неподдерживаемый формат изображения')
                    info['is_valid'] = False

                return info

        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f'Ошибка при обработке изображения: {str(e)}']
            }

    def generate_unique_filename(self, original_filename: str, person_id: Optional[int] = None) -> str:
        """Генерировать уникальное имя файла"""
        extension = Path(original_filename).suffix.lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]

        if person_id:
            return f"person_{person_id}_{timestamp}_{unique_id}{extension}"
        else:
            return f"temp_{timestamp}_{unique_id}{extension}"

    def get_file_hash(self, file_path: str) -> str:
        """Получить хэш файла"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    async def save_uploaded_file(
            self,
            file_data: bytes,
            original_filename: str,
            person_id: Optional[int] = None,
            temp: bool = False
    ) -> Dict[str, Any]:
        """Сохранить загруженный файл"""
        try:
            # Валидация расширения
            if not self.validate_file_extension(original_filename):
                raise FileValidationError(
                    f"Неподдерживаемое расширение файла. "
                    f"Разрешены: {', '.join(self.allowed_extensions)}"
                )

            # Валидация размера
            if not self.validate_file_size(len(file_data)):
                raise FileValidationError(
                    f"Файл слишком большой. Максимальный размер: "
                    f"{self.max_file_size / (1024 * 1024):.1f} MB"
                )

            # Генерируем уникальное имя файла
            unique_filename = self.generate_unique_filename(original_filename, person_id)

            # Определяем директорию для сохранения
            if temp:
                save_dir = self.upload_path / 'temp'
            elif person_id:
                save_dir = self.upload_path / 'persons' / str(person_id)
                save_dir.mkdir(parents=True, exist_ok=True)
            else:
                save_dir = self.upload_path / 'temp'

            file_path = save_dir / unique_filename

            # Сохраняем файл
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_data)

            # Валидация содержимого изображения
            image_info = await self.validate_image_content(str(file_path))

            if not image_info['is_valid']:
                # Удаляем некорректный файл
                await self.delete_file(str(file_path))
                raise FileValidationError('; '.join(image_info['errors']))

            # Получаем хэш файла
            file_hash = self.get_file_hash(str(file_path))

            result = {
                'filename': unique_filename,
                'original_filename': original_filename,
                'file_path': str(file_path),
                'relative_path': str(file_path.relative_to(self.upload_path)),
                'file_size': len(file_data),
                'file_hash': file_hash,
                'person_id': person_id,
                'is_temp': temp,
                'image_info': image_info
            }

            logger.info("File saved successfully",
                        filename=unique_filename,
                        size=len(file_data),
                        person_id=person_id)

            return result

        except FileValidationError:
            raise
        except Exception as e:
            logger.error("Failed to save file", error=str(e), filename=original_filename)
            raise FileStorageError(f"Не удалось сохранить файл: {str(e)}")

    async def delete_file(self, file_path: str) -> bool:
        """Удалить файл"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info("File deleted", file_path=file_path)
                return True
            return False

        except Exception as e:
            logger.error("Failed to delete file", error=str(e), file_path=file_path)
            return False

    async def cleanup_temp_files(self, older_than_hours: int = 24) -> int:
        """Очистить старые временные файлы"""
        temp_dir = self.upload_path / 'temp'
        if not temp_dir.exists():
            return 0

        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)

        try:
            for file_path in temp_dir.iterdir():
                if file_path.is_file():
                    file_stat = file_path.stat()
                    if file_stat.st_mtime < cutoff_time:
                        await self.delete_file(str(file_path))
                        deleted_count += 1

            logger.info("Temp files cleanup completed",
                        deleted_count=deleted_count,
                        older_than_hours=older_than_hours)

        except Exception as e:
            logger.error("Failed to cleanup temp files", error=str(e))

        return deleted_count


# Глобальный экземпляр сервиса
file_service = FileService()