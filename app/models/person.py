from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class PersonBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class PhotoBase(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(..., min_length=1, max_length=500)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    is_active: bool = True


class PhotoCreate(PhotoBase):
    person_id: int
    embedding_vector: Optional[List[float]] = None


class Photo(PhotoBase):
    id: int
    person_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Person(PersonBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PersonWithPhotos(Person):
    photos: List[Photo] = []

    class Config:
        from_attributes = True


class IdentificationResult(BaseModel):
    person_id: Optional[int] = None
    person_name: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    similarity: float = Field(0.0, ge=0.0)  # Убираем верхний предел
    is_match: bool = False
    photo_id: Optional[int] = None

    @field_validator('similarity', 'confidence')
    @classmethod
    def clamp_values(cls, v):
        """Обрезаем значения до разумных пределов"""
        if v > 1.0:
            return 1.0
        elif v < 0.0:
            return 0.0
        return v


class PersonStats(BaseModel):
    total_photos: int
    active_photos: int
    avg_confidence: float
    last_photo_date: Optional[datetime]