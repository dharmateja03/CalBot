"""
CalBot FastAPI Application
Main entry point for the backend API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, chat, calendar, preferences

# Initialize FastAPI app
app = FastAPI(
    title="CalBot API",
    description="AI Smart Scheduler - Natural language calendar management",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
app.include_router(preferences.router, prefix="/preferences", tags=["Preferences"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "CalBot API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "calbot-api",
        "version": "1.0.0"
    }
