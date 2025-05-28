# routers/words.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from calendar import monthrange

from database import get_db
from models.word import Word
from schemas.word_schemas import WordCreate, WordUpdate, WordResponse, DifficultyLevel

router = APIRouter()

@router.post("/words", response_model=WordResponse)
def create_word(word_data: WordCreate, db: Session = Depends(get_db)):
    """Create a new vocabulary word"""
    # Check if term already exists
    existing_word = db.query(Word).filter(Word.term.ilike(word_data.term)).first()
    if existing_word:
        raise HTTPException(status_code=400, detail=f"Term '{word_data.term}' already exists")
    
    # Create new word
    db_word = Word(
        term=word_data.term.lower().strip(),
        pronunciation=word_data.pronunciation,
        definition=word_data.definition,
        example=word_data.example,
        category=word_data.category,
        difficulty=word_data.difficulty.value,
        date_published=word_data.date_published
    )
    db.add(db_word)
    db.commit()
    db.refresh(db_word)
    
    return db_word

@router.get("/words", response_model=List[WordResponse])
def get_words(
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty level"),
    search: Optional[str] = Query(None, description="Search in term and definition"),
    date_from: Optional[date] = Query(None, description="Filter words published from this date"),
    date_to: Optional[date] = Query(None, description="Filter words published until this date"),
    published_today: Optional[bool] = Query(None, description="Filter words published today"),
    published_only: Optional[bool] = Query(None, description="Show only published words (with date_published)"),
    unpublished_only: Optional[bool] = Query(None, description="Show only unpublished words (without date_published)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get all words with optional filtering and pagination"""
    query = db.query(Word)
    
    # Category filter
    if category:
        query = query.filter(Word.category.ilike(f"%{category}%"))
    
    # Difficulty filter
    if difficulty:
        query = query.filter(Word.difficulty == difficulty.value)
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Word.term.ilike(search_term)) |
            (Word.definition.ilike(search_term)) |
            (Word.example.ilike(search_term))
        )
    
    # Publication status filters
    if published_only:
        query = query.filter(Word.date_published.isnot(None))
    elif unpublished_only:
        query = query.filter(Word.date_published.is_(None))
    
    # Date filtering
    if published_today:
        today = date.today()
        query = query.filter(Word.date_published == today)
    elif date_from and date_to:
        query = query.filter(Word.date_published.between(date_from, date_to))
    elif date_from:
        query = query.filter(Word.date_published >= date_from)
    elif date_to:
        query = query.filter(Word.date_published <= date_to)
    
    # Order by date_published (newest first), with unpublished items last
    words = query.order_by(
        Word.date_published.desc().nulls_last(),
        Word.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return words

@router.get("/words/daily", response_model=List[WordResponse])
def get_daily_words(
    target_date: Optional[date] = Query(None, description="Get words for specific date (default: today)"),
    db: Session = Depends(get_db)
):
    """Get words published on a specific date (default: today)"""
    if target_date is None:
        target_date = date.today()
    
    words = db.query(Word).filter(
        Word.date_published == target_date
    ).order_by(Word.created_at).all()
    
    return words

@router.get("/words/search/{term}", response_model=WordResponse)
def search_word_by_term(term: str, db: Session = Depends(get_db)):
    """Search for a word by exact term match"""
    word = db.query(Word).filter(Word.term.ilike(term.lower().strip())).first()
    if not word:
        raise HTTPException(status_code=404, detail=f"Word '{term}' not found")
    return word

@router.get("/words/{word_id}", response_model=WordResponse)
def get_word(word_id: int, db: Session = Depends(get_db)):
    """Get a specific word by ID"""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    return word

@router.get("/words/daily/random", response_model=WordResponse)
def get_random_daily_word(
    target_date: Optional[date] = Query(None, description="Get random word for specific date (default: today)"),
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty level"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """Get a random word published on a specific date"""
    if target_date is None:
        target_date = date.today()
    
    query = db.query(Word).filter(Word.date_published == target_date)
    
    if difficulty:
        query = query.filter(Word.difficulty == difficulty.value)
    if category:
        query = query.filter(Word.category.ilike(f"%{category}%"))
    
    # Get random word using SQL ORDER BY RANDOM()
    word = query.order_by(db.func.random()).first()
    
    if not word:
        raise HTTPException(
            status_code=404, 
            detail=f"No words found for date {target_date}" + 
                   (f" with difficulty {difficulty}" if difficulty else "") +
                   (f" in category {category}" if category else "")
        )
    
    return word

@router.get("/words/monthly/{year}/{month}", response_model=List[WordResponse])
def get_monthly_words(
    year: int, 
    month: int,
    db: Session = Depends(get_db)
):
    """Get all words published in a specific month"""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    
    if year < 2020 or year > 2030:
        raise HTTPException(status_code=400, detail="Year must be between 2020 and 2030")
    
    # Get first and last day of the month
    _, last_day = monthrange(year, month)
    
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    
    words = db.query(Word).filter(
        Word.date_published.between(start_date, end_date)
    ).order_by(Word.date_published.asc()).all()
    
    return words

@router.get("/words/upcoming", response_model=List[WordResponse])
def get_upcoming_words(
    days: int = Query(7, ge=1, le=365, description="Number of days to look ahead"),
    db: Session = Depends(get_db)
):
    """Get words scheduled for publication in the next N days"""
    today = date.today()
    future_date = date.fromordinal(today.toordinal() + days)
    
    words = db.query(Word).filter(
        Word.date_published.between(today, future_date)
    ).order_by(Word.date_published.asc()).all()
    
    return words

@router.put("/words/{word_id}", response_model=WordResponse)
def update_word(word_id: int, word_update: WordUpdate, db: Session = Depends(get_db)):
    """Update a word by ID"""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    # Update fields
    update_data = word_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "difficulty" and value:
            setattr(word, field, value.value)
        elif field == "term" and value:
            # Check if new term already exists
            existing = db.query(Word).filter(
                Word.term.ilike(value), 
                Word.id != word_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Term '{value}' already exists")
            setattr(word, field, value.lower().strip())
        else:
            setattr(word, field, value)
    
    word.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(word)
    
    return word

@router.patch("/words/{word_id}/publish")
def publish_word(
    word_id: int, 
    publish_date: Optional[date] = Query(None, description="Publication date (default: today)"),
    db: Session = Depends(get_db)
):
    """Publish a word by setting its publication date"""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    if publish_date is None:
        publish_date = date.today()
    
    word.date_published = publish_date
    word.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(word)
    
    return {
        "message": f"Word '{word.term}' published for {publish_date}",
        "word_id": word.id,
        "publication_date": publish_date
    }

@router.patch("/words/{word_id}/unpublish")
def unpublish_word(word_id: int, db: Session = Depends(get_db)):
    """Unpublish a word by removing its publication date"""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    word.date_published = None
    word.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(word)
    
    return {
        "message": f"Word '{word.term}' unpublished",
        "word_id": word.id
    }

@router.delete("/words/{word_id}")
def delete_word(word_id: int, db: Session = Depends(get_db)):
    """Delete a word by ID"""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")
    
    term = word.term
    db.delete(word)
    db.commit()
    return {"message": f"Word '{term}' deleted successfully"}

@router.get("/words/stats/categories")
def get_categories(db: Session = Depends(get_db)):
    """Get all unique categories with word counts"""
    categories = db.query(
        Word.category,
        db.func.count(Word.id).label('count')
    ).filter(
        Word.category.isnot(None)
    ).group_by(Word.category).all()
    
    return {
        "categories": [
            {"name": cat.category, "count": cat.count} 
            for cat in categories
        ],
        "total_categories": len(categories)
    }

@router.get("/words/stats/summary")
def get_word_stats(db: Session = Depends(get_db)):
    """Get comprehensive word statistics"""
    total_words = db.query(Word).count()
    published_words = db.query(Word).filter(Word.date_published.isnot(None)).count()
    unpublished_words = total_words - published_words
    
    # Words by difficulty
    by_difficulty = {}
    for difficulty in DifficultyLevel:
        count = db.query(Word).filter(Word.difficulty == difficulty.value).count()
        by_difficulty[difficulty.value] = count
    
    # Categories count
    categories_count = db.query(Word.category).distinct().filter(
        Word.category.isnot(None)
    ).count()
    
    # Today's words
    today = date.today()
    todays_words = db.query(Word).filter(Word.date_published == today).count()
    
    # This week's words
    week_start = date.fromordinal(today.toordinal() - today.weekday())
    week_end = date.fromordinal(week_start.toordinal() + 6)
    this_weeks_words = db.query(Word).filter(
        Word.date_published.between(week_start, week_end)
    ).count()
    
    # This month's words
    month_start = date(today.year, today.month, 1)
    if today.month == 12:
        month_end = date(today.year + 1, 1, 1)
    else:
        month_end = date(today.year, today.month + 1, 1)
    month_end = date.fromordinal(month_end.toordinal() - 1)
    
    this_months_words = db.query(Word).filter(
        Word.date_published.between(month_start, month_end)
    ).count()
    
    return {
        "total_words": total_words,
        "published_words": published_words,
        "unpublished_words": unpublished_words,
        "todays_words": todays_words,
        "this_weeks_words": this_weeks_words,
        "this_months_words": this_months_words,
        "words_by_difficulty": by_difficulty,
        "total_categories": categories_count
    }

@router.get("/words/stats/calendar/{year}/{month}")
def get_calendar_stats(year: int, month: int, db: Session = Depends(get_db)):
    """Get word publication calendar for a specific month"""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    
    # Get all days in the month with word counts
    _, last_day = monthrange(year, month)
    
    calendar_data = []
    for day in range(1, last_day + 1):
        target_date = date(year, month, day)
        word_count = db.query(Word).filter(Word.date_published == target_date).count()
        
        calendar_data.append({
            "date": target_date.isoformat(),
            "day": day,
            "word_count": word_count,
            "has_words": word_count > 0
        })
    
    return {
        "year": year,
        "month": month,
        "calendar": calendar_data,
        "total_days": last_day,
        "days_with_words": sum(1 for day in calendar_data if day["has_words"])
    }