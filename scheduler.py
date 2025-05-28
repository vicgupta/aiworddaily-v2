from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import sessionmaker
from database import engine
from models.user import User
from models.word import Word
from email_service import email_service
from datetime import date
import logging
import pytz


logger = logging.getLogger(__name__)

# Create database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
eastern = pytz.timezone('US/Eastern')

class EmailScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    def start(self):
        """Start the scheduler"""

        self.scheduler.add_job(
            func=self.send_daily_word_emails,
            # trigger=CronTrigger(hour=8, minute=1, timezone='UTC'),  # Adjust to your timezone
            # trigger=CronTrigger(hour=5, minute=0, timezone=pytz.UTC),
            trigger=CronTrigger(hour=6, minute=14, timezone=eastern),  # Adjust to your timezone
            name='AI Daily Word Email',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Email scheduler started successfully")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Email scheduler stopped")
    
    async def send_daily_word_emails(self):
        """Send today's word to all users"""
        try:
            db = SessionLocal()
            
            # Get today's word
            today = date.today()
            word = db.query(Word).filter(Word.date_published == today).first()
            
            # If no word for today, get the most recent published word
            if not word:
                word = db.query(Word).filter(
                    Word.date_published.isnot(None)
                ).order_by(Word.date_published.desc()).first()
            
            if not word:
                logger.warning("No words available to send")
                return
            
            # Get all users
            users = db.query(User).all()
            
            if not users:
                logger.info("No users found to send emails to")
                return
            
            # Prepare word data
            word_data = {
                'term': word.term,
                'pronunciation': word.pronunciation,
                'definition': word.definition,
                'example': word.example,
                'category': word.category,
                'difficulty': word.difficulty,
                'date_published': word.date_published.isoformat() if word.date_published else None
            }
            
            # Send emails in batches to avoid overwhelming the email server
            batch_size = 10
            user_batches = [users[i:i + batch_size] for i in range(0, len(users), batch_size)]
            
            total_sent = 0
            for batch in user_batches:
                batch_emails = []
                for user in batch:
                    batch_emails.append(user.email)
                
                # Create email content (using first user's name for batch)
                html_content, text_content = email_service.create_word_email(
                    word_data, 
                    batch[0].name if batch else "Friend"
                )
                # print (html_content, text_content)
                
                # Send email
                subject = f"🤖 Your AI Word Daily: {word.term.title()}"
                print (subject)
                success = email_service.send_email(
                    to_emails=batch_emails,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                print (success)
                if success:
                    total_sent += len(batch_emails)
            
            logger.info(f"Daily word emails sent successfully to {total_sent} users")
            
        except Exception as e:
            logger.error(f"Failed to send daily word emails: {str(e)}")
        
        finally:
            db.close()

# Create global instance
email_scheduler = EmailScheduler()