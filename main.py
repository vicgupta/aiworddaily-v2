from fastapi import FastAPI, HTTPException, Query, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import users, words
from scheduler import email_scheduler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title="AI Word Daily API", 
    version="1.0.0",
    description="API for AI Word Daily vocabulary learning platform"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://www.hiblazar.com", "https://www.hiblazar.com", "https://hiblazar.com", "http://hiblazar.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(words.router, prefix="/api/v1", tags=["words"])

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Word Daily API"}

@app.on_event("startup")
async def startup_event():
    """Start the email scheduler when the app starts"""
    try:
        email_scheduler.start()
        logger.info("Application started successfully with email scheduler")
    except Exception as e:
        logger.error(f"Failed to start email scheduler: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the email scheduler when the app shuts down"""
    try:
        email_scheduler.stop()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during application shutdown: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)