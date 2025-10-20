"""
Calendar routes
Google Calendar integration endpoints
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import httpx

from app.services.calendar_service import GoogleCalendarService

router = APIRouter()

class CalendarEvent(BaseModel):
    id: str
    title: str
    start: datetime
    end: datetime
    description: Optional[str] = None

class AvailableSlot(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: int

async def get_user_credentials(user_id: str) -> Optional[dict]:
    """Fetch user's Google OAuth tokens from auth service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:8000/auth/tokens/{user_id}")
            if response.status_code == 200:
                return response.json()
            else:
                return None
    except Exception as e:
        print(f"⚠️  Failed to fetch user credentials: {e}")
        return None


@router.get("/events")
async def get_calendar_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Fetch Google Calendar events for display
    Query params: start_date, end_date (ISO format)
    """
    # Extract user_id from JWT token (simplified - you should verify the token)
    user_id = "demo_user"  # Default

    if authorization and authorization.startswith("Bearer "):
        import jwt
        import os
        token = authorization.replace("Bearer ", "")
        try:
            payload = jwt.decode(token, os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production"), algorithms=["HS256"])
            user_id = payload.get("user_id", "demo_user")
        except:
            pass

    # Get user credentials
    user_credentials = await get_user_credentials(user_id)

    if not user_credentials:
        print(f"⚠️  No credentials for user {user_id}, returning empty events")
        return {"events": []}

    # Initialize calendar service
    calendar_service = GoogleCalendarService(
        user_id=user_id,
        credentials_dict=user_credentials
    )

    # Parse dates
    if start_date:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    else:
        start = datetime.now()

    if end_date:
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    else:
        from datetime import timedelta
        end = start + timedelta(days=30)

    print(f"📅 Fetching events from {start} to {end} for user {user_id}")

    # Fetch events from Google Calendar
    try:
        events = calendar_service.get_events(start, end)
        print(f"✅ Found {len(events)} events")
        return {"events": events}
    except Exception as e:
        print(f"❌ Error fetching events: {e}")
        import traceback
        traceback.print_exc()
        return {"events": []}

@router.post("/sync")
async def sync_calendar():
    """Force sync with Google Calendar"""
    # TODO: Fetch latest events from Google Calendar
    # TODO: Update local cache
    return {
        "synced": True,
        "events_imported": 0,
        "last_sync": datetime.now().isoformat()
    }

@router.get("/availability")
async def get_availability(start_date: str, end_date: str):
    """
    Get available time slots within date range
    Used by scheduling algorithm
    """
    # TODO: Fetch calendar events
    # TODO: Calculate free slots based on work hours
    # TODO: Respect user preferences (breaks, etc.)
    return {
        "available_slots": []
    }

@router.get("/event/{event_id}/url")
async def get_google_calendar_url(event_id: str):
    """Get Google Calendar URL for specific event"""
    return {
        "url": f"https://calendar.google.com/calendar/r/eventedit/{event_id}"
    }
