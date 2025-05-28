# ===== models/word.py =====
from sqlalchemy import Column, Integer, String, DateTime, Text, Index, Date
from datetime import datetime
from database import Base

class Word(Base):
    __tablename__ = "words"
    
    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(100), unique=True, index=True, nullable=False)  # Add length
    pronunciation = Column(String(200), nullable=True)
    definition = Column(Text, nullable=False)
    example = Column(Text, nullable=True)
    category = Column(String(50), index=True, nullable=True)
    difficulty = Column(String(20), nullable=False, default="beginner")
    date_published = Column(Date, nullable=True, index=True)  # New field
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add composite indexes for better query performance
    __table_args__ = (
        Index('idx_category_difficulty', 'category', 'difficulty'),
        Index('idx_term_category', 'term', 'category'),
    )