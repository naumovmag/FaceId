# Face Recognition System

Система распознавания лиц на основе FastAPI и InsightFace для идентификации людей по фотографиям с современным веб-интерфейсом и REST API.

## ✨ Возможности

- 🔍 **Идентификация лиц** - быстрое распознавание людей по фотографиям с точностью >99%
- 📈 **Автообучение** - успешные распознавания автоматически добавляют новые фото в базу
- 👥 **Управление людьми** - полноценная система управления профилями людей
- 📸 **Загрузка фотографий** - drag-and-drop загрузка с предварительным просмотром
- 📊 **Детальная статистика** - аналитика по людям, фотографиям и точности распознавания
- 🎯 **Высокая точность** - использование модели InsightFace buffalo_l
- 🖥️ **Современный интерфейс** - адаптивный веб-интерфейс с Bootstrap 5
- 🚀 **REST API** - полноценное API с автоматической документацией
- ⚡ **Высокая производительность** - оптимизированная обработка изображений
- 🔒 **Локальное хранение** - все данные остаются на вашем сервере

## 🛠 Технологии

- **FastAPI** - современный веб-фреймворк с автогенерацией документации
- **SQLAlchemy** - мощная ORM для работы с базой данных
- **SQLite** - встроенная база данных (легко заменить на PostgreSQL)
- **InsightFace** - передовая библиотека для распознавания лиц
- **OpenCV** - профессиональная библиотека компьютерного зрения
- **Pydantic** - валидация данных с автоматической типизацией
- **Bootstrap 5** - современный CSS фреймворк для адаптивного интерфейса
- **Jinja2** - мощный шаблонизатор для веб-страниц

## 📋 Системные требования

- **Python** 3.8+ (рекомендуется 3.11+)
- **ОЗУ**: минимум 4GB, рекомендуется 8GB+
- **Диск**: ~3GB свободного места (модели InsightFace + данные)
- **ОС**: Linux, macOS, Windows
- **CPU**: любой современный процессор (оптимизировано для CPU)

## 🚀 Быстрый старт

### 1. Установка

```bash
# Клонируйте репозиторий
git clone git@github.com:naumovmag/FaceId.git
cd FaceId

# Создайте и активируйте виртуальное окружение
python -m venv .venv

# Активация окружения:
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Установите зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Настройка

```bash
# Скопируйте файл настроек
cp .env.example .env

# Отредактируйте настройки при необходимости
nano .env
```

Основные настройки в `.env`:

```env
# Основные настройки
APP_HOST=127.0.0.1          # Хост приложения
APP_PORT=8000               # Порт приложения  
DEBUG=True                  # Режим отладки
SECRET_KEY=your_secret_key  # Секретный ключ (измените для продакшена!)

# Распознавание лиц
FACE_RECOGNITION_THRESHOLD=0.6  # Порог сходства (0.4-0.8)
MAX_UPLOAD_SIZE=10485760       # Макс. размер файла (10MB)

# Пути
UPLOAD_PATH=./uploads          # Путь для загрузок
MODELS_CACHE_PATH=./models_cache  # Кэш моделей
```

> 💡 **Важно**: Обязательно измените `SECRET_KEY` для продакшен-окружения!

### 3. Запуск

```bash
# Простой запуск
python run.py

# Или через uvicorn напрямую
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

🌐 **Приложение доступно по адресу: http://127.0.0.1:8000**

### 4. Первые шаги

1. **Добавьте людей**: перейдите в раздел "Люди" → "Добавить человека"
2. **Загрузите фотографии**: в разделе "Загрузка" добавьте фото к профилям
3. **Тестируйте распознавание**: в разделе "Идентификация" загрузите фото для поиска

## 💻 Интерфейс

### Веб-интерфейс

- **🏠 Главная** (`/`) - обзор системы и быстрые ссылки
- **🔍 Идентификация** (`/identify`) - загрузка фото для распознавания
- **📤 Загрузка** (`/upload`) - добавление фотографий к профилям людей
- **👥 Люди** (`/persons`) - управление профилями людей
- **⚙️ Управление** (`/training`) - статистика и настройки системы

### REST API 

Автоматическая документация доступна по адресам:
- **📖 Swagger UI**: http://127.0.0.1:8000/docs
- **📚 ReDoc**: http://127.0.0.1:8000/redoc

#### Основные эндпоинты:

**👥 Управление людьми:**
```bash
POST   /api/persons           # Создать человека
GET    /api/persons           # Список людей  
GET    /api/persons/{id}      # Информация о человеке
PUT    /api/persons/{id}      # Обновить человека
DELETE /api/persons/{id}      # Удалить человека
GET    /api/persons/{id}/stats # Статистика человека
```

**📸 Работа с фотографиями:**
```bash
POST   /api/persons/{id}/photos  # Загрузить фото
DELETE /api/photos/{id}          # Удалить фото
```

**🔍 Идентификация:**
```bash
POST   /api/identify  # Распознать лицо по фото (опционально person_id для привязки)
```

**📊 Система:**
```bash
GET    /api/health    # Проверка состояния
GET    /api/stats     # Статистика системы
```

## 📖 Примеры использования

### Python API клиент

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

# Создание человека
def create_person(name: str):
    response = requests.post(f"{BASE_URL}/persons", 
                           json={"name": name})
    return response.json()

# Загрузка фотографии
def upload_photo(person_id: int, image_path: str):
    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post(f"{BASE_URL}/persons/{person_id}/photos", 
                               files=files)
    return response.json()

# Идентификация лица
def identify_face(image_path: str):
    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post(f"{BASE_URL}/identify", 
                               files=files)
    return response.json()

# Пример использования
if __name__ == "__main__":
    # 1. Создаем человека
    person = create_person("Иван Иванов")
    print(f"Создан человек: {person}")
    
    # 2. Загружаем фото
    photo_result = upload_photo(person["id"], "ivan_photo.jpg")
    print(f"Фото загружено: {photo_result}")
    
    # 3. Тестируем распознавание
    identify_result = identify_face("test_photo.jpg")
    if identify_result["is_match"]:
        print(f"✅ Найден: {identify_result['person_name']}")
        print(f"   Сходство: {identify_result['similarity']:.1%}")
    else:
        print("❌ Лицо не распознано")
```

### cURL примеры

```bash
# Создать человека
curl -X POST "http://127.0.0.1:8000/api/persons" \
     -H "Content-Type: application/json" \
     -d '{"name": "Анна Петрова"}'

# Загрузить фотографию
curl -X POST "http://127.0.0.1:8000/api/persons/1/photos" \
     -F "file=@photo.jpg"

# Идентифицировать лицо
curl -X POST "http://127.0.0.1:8000/api/identify" \
     -F "file=@unknown_face.jpg"

# Получить статистику
curl "http://127.0.0.1:8000/api/stats"
```

### JavaScript (браузер)

```javascript
// Идентификация лица через JavaScript
async function identifyFace(fileInput) {
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    try {
        const response = await fetch('/api/identify', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.is_match) {
            console.log(`Найден: ${result.person_name}`);
            console.log(`Сходство: ${(result.similarity * 100).toFixed(1)}%`);
        } else {
            console.log('Лицо не найдено в базе данных');
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
}
```

## 📁 Структура проекта

```
face_recognition_app/
├── 📁 app/                    # Основное приложение
│   ├── 📁 config/             # Конфигурация
│   │   ├── settings.py        # Настройки приложения
│   │   └── database.py        # Подключение к БД
│   ├── 📁 models/             # Модели данных  
│   │   ├── person.py          # Pydantic модели
│   │   └── database.py        # SQLAlchemy модели
│   ├── 📁 services/           # Бизнес-логика
│   │   ├── face_service.py    # Сервис распознавания лиц
│   │   ├── person_service.py  # Сервис управления людьми
│   │   └── file_service.py    # Сервис работы с файлами
│   ├── 📁 routes/             # Маршруты
│   │   ├── api.py             # REST API эндпоинты
│   │   └── web.py             # Веб-страницы
│   ├── 📁 utils/              # Утилиты
│   │   ├── validators.py      # Валидаторы данных
│   │   └── exceptions.py      # Кастомные исключения
│   └── main.py                # Главный файл FastAPI
├── 📁 static/                 # Статические файлы
│   └── 📁 css/
│       └── style.css          # Стили интерфейса
├── 📁 templates/              # HTML шаблоны
│   ├── base.html              # Базовый шаблон
│   ├── index.html             # Главная страница
│   ├── identify.html          # Идентификация
│   ├── upload.html            # Загрузка фото
│   ├── persons_list.html      # Список людей
│   ├── person_detail.html     # Детали человека
│   ├── training.html          # Управление системой
│   └── results.html           # Результаты идентификации
├── 📁 uploads/                # Загруженные файлы
│   ├── 📁 persons/            # Фото людей (по ID)
│   ├── 📁 temp/               # Временные файлы
│   └── 📁 debug/              # Файлы для отладки
├── 📁 models_cache/           # Кэш моделей InsightFace
├── 📄 requirements.txt        # Python зависимости
├── 📄 .env.example            # Пример файла настроек
├── 📄 run.py                  # Скрипт запуска
├── 📄 face_recognition.db     # База данных SQLite (создается автоматически)
└── 📄 README.md               # Документация
```

## ⚙️ Настройка и оптимизация

### 🎯 Настройка точности распознавания

Порог `FACE_RECOGNITION_THRESHOLD` в `.env` влияет на строгость сравнения:

- **0.4-0.5** - Менее строгое сравнение, больше совпадений
- **0.6** - ⭐ Оптимальное значение (по умолчанию)  
- **0.7-0.8** - Более строгое сравнение, меньше ложных срабатываний

### 🚀 Оптимизация производительности

```env
# Настройки для CPU оптимизации
OMP_NUM_THREADS=1           # Потоки OpenMP
ONNX_NUM_THREADS=1          # Потоки ONNX Runtime
INSIGHTFACE_ROOT=./models_cache  # Кэш моделей

# Размеры файлов
MAX_UPLOAD_SIZE=10485760    # 10MB макс. размер
```

### 📊 Рекомендации по качеству фотографий

**✅ Хорошие фото:**
- Разрешение от 200x200 пикселей
- Хорошее освещение лица
- Лицо занимает >10% изображения
- Четкость, отсутствие размытия
- Фронтальный или полуфронтальный ракурс

**❌ Плохие фото:**
- Слишком темные или пересвеченные
- Сильное размытие или шум
- Лицо сбоку (>45° поворот)
- Закрытое лицо (маска, очки, волосы)
- Разрешение менее 100x100 пикселей

### 🔧 Расширенные настройки

```python
# В face_service.py можно настроить параметры детекции:
self.face_app.prepare(
    ctx_id=0,                    # GPU: 0+, CPU: -1
    det_size=(640, 640),         # Размер для детекции (больше = точнее, медленнее)
    det_thresh=0.5               # Порог детекции лица
)
```



## 🔧 Разработка и развертывание

### 🛠 Разработка

```bash
# Запуск в режиме разработки с автоперезагрузкой
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Форматирование кода
black app/
isort app/

# Типизация
mypy app/
```

### 🚀 Продакшен

```bash
# Установка для продакшена
pip install gunicorn

# Запуск с Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 --timeout 300

# Docker (опционально)
docker build -t face-recognition-system .
docker run -p 8000:8000 -v ./uploads:/app/uploads face-recognition-system
```

### 📊 Мониторинг

- **Автоматическая документация**: http://127.0.0.1:8000/docs
- **Альтернативная документация**: http://127.0.0.1:8000/redoc  
- **Проверка состояния**: http://127.0.0.1:8000/api/health
- **Статистика системы**: http://127.0.0.1:8000/api/stats

### 🔗 Полезные ссылки

- **🏠 Репозиторий**: [github.com/naumovmag/FaceId](https://github.com/naumovmag/FaceId)
- **📚 InsightFace**: [github.com/deepinsight/insightface](https://github.com/deepinsight/insightface)
- **⚡ FastAPI**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **🗄️ SQLAlchemy**: [sqlalchemy.org](https://www.sqlalchemy.org)

---

## 📄 Лицензия

Свободное использование в некоммерческих целях.

## 👥 Контрибьюторы

Проект разработан с использованием современных технологий и лучших практик Python-разработки.

⭐ **Поставьте звезду проекту, если он оказался полезным!**