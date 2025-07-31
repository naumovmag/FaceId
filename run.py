#!/usr/bin/env python3
"""
Скрипт запуска приложения Face Recognition System
"""
import os
import sys
import uvicorn
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import settings


def main():
    """Главная функция запуска"""

    # Проверяем необходимые директории
    required_dirs = [
        Path(settings.upload_path),
        Path(settings.models_cache_path),
        Path("static"),
        Path("templates")
    ]

    for directory in required_dirs:
        directory.mkdir(parents=True, exist_ok=True)

    print("🚀 Запуск Face Recognition System...")
    print(f"📍 Адрес: http://{settings.app_host}:{settings.app_port}")
    print(f"🔧 Режим отладки: {settings.debug}")
    print(f"📊 База данных: {settings.database_url}")
    print(f"🎯 Порог распознавания: {settings.face_recognition_threshold}")

    # Устанавливаем переменные окружения для ONNX
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['ONNX_NUM_THREADS'] = '1'
    os.environ['INSIGHTFACE_ROOT'] = settings.models_cache_path

    try:
        uvicorn.run(
            "app.main:app",
            host=settings.app_host,
            port=settings.app_port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Приложение остановлено пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
