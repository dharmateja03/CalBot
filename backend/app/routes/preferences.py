"""
Preferences routes
User settings and preferences management
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class WorkHours(BaseModel):
    start: str  # "09:00"
    end: str    # "17:00"

class BreakTime(BaseModel):
    start: str  # "12:00"
    end: str    # "13:00"

class Preferences(BaseModel):
    work_hours: WorkHours
    break_time: Optional[BreakTime] = None
    timezone: str
    preferred_deep_work_time: Optional[str] = None  # "morning", "afternoon", "evening"
    preferred_meeting_time: Optional[str] = None

@router.get("")
async def get_preferences():
    """Get user preferences"""
    # TODO: Fetch from database
    return {
        "work_hours": {
            "start": "09:00",
            "end": "17:00"
        },
        "break_time": {
            "start": "12:00",
            "end": "13:00"
        },
        "timezone": "America/New_York",
        "preferred_deep_work_time": "morning",
        "preferred_meeting_time": "afternoon"
    }

@router.put("")
async def update_preferences(preferences: Preferences):
    """Update user preferences"""
    # TODO: Validate preferences
    # TODO: Save to database
    return {
        "message": "Preferences updated successfully",
        "preferences": preferences
    }
