# ===== schemas/__init__.py =====
from .user_schemas import UserCreate, UserUpdate, UserResponse
from .word_schemas import WordCreate, WordUpdate, WordResponse, DifficultyLevel

__all__ = [
    "UserCreate", "UserUpdate", "UserResponse",
    "WordCreate", "WordUpdate", "WordResponse", "DifficultyLevel"
]
