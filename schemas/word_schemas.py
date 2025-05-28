from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional
from enum import Enum

class DifficultyLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"

class WordCreate(BaseModel):
    term: str
    pronunciation: Optional[str] = None
    definition: str
    example: Optional[str] = None
    category: Optional[str] = None
    difficulty: DifficultyLevel = DifficultyLevel.beginner
    date_published: Optional[date] = None  # New field

class WordUpdate(BaseModel):
    term: Optional[str] = None
    pronunciation: Optional[str] = None
    definition: Optional[str] = None
    example: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    date_published: Optional[date] = None  # New field

class WordResponse(BaseModel):
    id: int
    term: str
    pronunciation: Optional[str]
    definition: str
    example: Optional[str]
    category: Optional[str]
    difficulty: str
    date_published: Optional[date]  # New field
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True