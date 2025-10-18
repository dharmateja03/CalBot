"""
Google Calendar Service
Handles all Google Calendar API interactions
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarService:
    """Interface for Google Calendar operations"""

    def __init__(self, user_id: Optional[str] = None, credentials_dict: Optional[Dict] = None):
        """
        Initialize calendar service with user credentials

        Args:
            user_id: User ID to fetch tokens for (from auth service)
            credentials_dict: Direct credentials dictionary (access_token, refresh_token, etc.)
        """
        self.user_id = user_id
        self.credentials_dict = credentials_dict
        self.service = None
        self.calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        self.timezone = os.getenv('TIMEZONE', 'UTC')

        # Initialize Google Calendar API client
        self._initialize_service()

    def _initialize_service(self):
        """Initialize the Google Calendar API service"""
        try:
            creds = None

            # Priority 1: Use credentials from constructor (passed from auth service)
            if self.credentials_dict:
                creds = Credentials(
                    token=self.credentials_dict.get('access_token'),
                    refresh_token=self.credentials_dict.get('refresh_token'),
                    token_uri=self.credentials_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
                    client_id=self.credentials_dict.get('client_id'),
                    client_secret=self.credentials_dict.get('client_secret'),
                    scopes=self.credentials_dict.get('scopes', SCOPES)
                )

                # Refresh if expired
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Update the credentials dict with new token
                    self.credentials_dict['access_token'] = creds.token
                    if creds.expiry:
                        self.credentials_dict['expiry'] = creds.expiry.isoformat()

            # Priority 2: Fallback to token.json for local development
            elif os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)

                # If expired, refresh
                if not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        # Save refreshed token
                        with open('token.json', 'w') as token:
                            token.write(creds.to_json())
                    else:
                        print("⚠️  Token expired and no refresh token available. Using mock mode.")
                        return

            # Priority 3: No credentials available - use mock mode
            else:
                print("⚠️  No credentials available. Using mock mode.")
                print("    To enable real Google Calendar:")
                print("    1. Run OAuth flow: Visit http://localhost:8000/auth/google")
                print("    2. Or provide credentials_dict when creating service")
                return

            # Build the Calendar API service
            self.service = build('calendar', 'v3', credentials=creds)
            print(f"✅ Google Calendar API initialized successfully for user: {self.user_id or 'local'}")

        except Exception as e:
            print(f"⚠️  Failed to initialize Google Calendar API: {e}")
            print("    Falling back to mock mode")
            self.service = None

    def get_events(
        self,
        start_date: datetime,
        end_date: datetime,
        calendar_id: str = "primary"
    ) -> List[Dict]:
        """
        Fetch events from Google Calendar

        Args:
            start_date: Start of time range
            end_date: End of time range
            calendar_id: Calendar ID (default: primary)

        Returns:
            List of calendar events
        """
        if not self.service:
            # Fallback to mock data if API not initialized
            return [
                {
                    "id": "mock_event_1",
                    "title": "Existing Meeting",
                    "start": (datetime.now() + timedelta(hours=2)).isoformat(),
                    "end": (datetime.now() + timedelta(hours=3)).isoformat(),
                    "description": "Mock event from Google Calendar"
                }
            ]

        try:
            # Convert to RFC3339 format with timezone
            time_min = start_date.isoformat() + 'Z' if start_date.tzinfo is None else start_date.isoformat()
            time_max = end_date.isoformat() + 'Z' if end_date.tzinfo is None else end_date.isoformat()

            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # Convert to our format
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                formatted_events.append({
                    'id': event['id'],
                    'title': event.get('summary', 'Untitled Event'),
                    'start': start,
                    'end': end,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'htmlLink': event.get('htmlLink', '')
                })

            return formatted_events

        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        calendar_id: str = "primary"
    ) -> Dict:
        """
        Create a new event in Google Calendar

        Args:
            title: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description (optional)
            calendar_id: Calendar ID (default: primary)

        Returns:
            Created event data
        """
        if not self.service:
            # Fallback to mock response if API not initialized
            event_id = f"calbot_{int(datetime.now().timestamp())}"
            return {
                "id": event_id,
                "title": title,
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "description": description,
                "calendar_url": f"https://calendar.google.com/calendar/r/eventedit/{event_id}",
                "status": "confirmed"
            }

        try:
            # Create event object
            event = {
                'summary': title,
                'description': description or '',
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': self.timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': self.timezone,
                },
                'reminders': {
                    'useDefault': True,
                },
            }

            # Create the event
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()

            return {
                "id": created_event['id'],
                "title": created_event.get('summary', title),
                "start": created_event['start'].get('dateTime', created_event['start'].get('date')),
                "end": created_event['end'].get('dateTime', created_event['end'].get('date')),
                "description": created_event.get('description', ''),
                "calendar_url": created_event.get('htmlLink', ''),
                "status": created_event.get('status', 'confirmed')
            }

        except HttpError as error:
            print(f"An error occurred creating event: {error}")
            # Return mock data on error
            event_id = f"calbot_{int(datetime.now().timestamp())}"
            return {
                "id": event_id,
                "title": title,
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "description": description,
                "calendar_url": "",
                "status": "error"
            }

    def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None,
        calendar_id: str = "primary"
    ) -> Dict:
        """
        Update an existing event

        Args:
            event_id: Event ID to update
            title: New title (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            description: New description (optional)
            calendar_id: Calendar ID (default: primary)

        Returns:
            Updated event data
        """
        if not self.service:
            # Mock response if API not initialized
            return {
                "id": event_id,
                "title": title,
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
                "description": description,
                "status": "confirmed"
            }

        try:
            # First, get the existing event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            # Update only the fields that were provided
            if title:
                event['summary'] = title
            if description is not None:
                event['description'] = description
            if start_time:
                event['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': self.timezone,
                }
            if end_time:
                event['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': self.timezone,
                }

            # Update the event
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            return {
                "id": updated_event['id'],
                "title": updated_event.get('summary', title),
                "start": updated_event['start'].get('dateTime', updated_event['start'].get('date')),
                "end": updated_event['end'].get('dateTime', updated_event['end'].get('date')),
                "description": updated_event.get('description', ''),
                "calendar_url": updated_event.get('htmlLink', ''),
                "status": updated_event.get('status', 'confirmed')
            }

        except HttpError as error:
            print(f"An error occurred updating event: {error}")
            # Return mock data on error
            return {
                "id": event_id,
                "title": title,
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
                "description": description,
                "status": "error"
            }

    def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary"
    ) -> bool:
        """
        Delete an event from Google Calendar

        Args:
            event_id: Event ID to delete
            calendar_id: Calendar ID (default: primary)

        Returns:
            True if successful
        """
        if not self.service:
            # Mock success if API not initialized
            print(f"📅 Mock: Deleted event {event_id}")
            return True

        try:
            # Delete the event
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            print(f"✅ Deleted event: {event_id}")
            return True

        except HttpError as error:
            print(f"❌ Error deleting event: {error}")
            return False

    def get_availability(
        self,
        start_date: datetime,
        end_date: datetime,
        work_hours_start: str = "09:00",
        work_hours_end: str = "17:00"
    ) -> List[Dict]:
        """
        Get available time slots within the given range

        Args:
            start_date: Start of date range
            end_date: End of date range
            work_hours_start: Work day start time (HH:MM)
            work_hours_end: Work day end time (HH:MM)

        Returns:
            List of available time slots
        """
        # Get existing events
        events = self.get_events(start_date, end_date)

        # TODO: Calculate free slots by subtracting busy times from work hours
        # For now, return mock available slots
        available_slots = []

        current_date = start_date.date()
        end_date_only = end_date.date()

        while current_date <= end_date_only:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                # Morning slot
                morning_start = datetime.combine(
                    current_date,
                    datetime.strptime(work_hours_start, "%H:%M").time()
                )
                morning_end = datetime.combine(
                    current_date,
                    datetime.strptime("12:00", "%H:%M").time()
                )

                # Afternoon slot
                afternoon_start = datetime.combine(
                    current_date,
                    datetime.strptime("13:00", "%H:%M").time()
                )
                afternoon_end = datetime.combine(
                    current_date,
                    datetime.strptime(work_hours_end, "%H:%M").time()
                )

                available_slots.append({
                    "start": morning_start.isoformat(),
                    "end": morning_end.isoformat(),
                    "duration_minutes": 180
                })

                available_slots.append({
                    "start": afternoon_start.isoformat(),
                    "end": afternoon_end.isoformat(),
                    "duration_minutes": 240
                })

            current_date += timedelta(days=1)

        return available_slots


def find_best_time_slot(
    available_slots: List[Dict],
    duration_minutes: int,
    preferred_time: Optional[str] = None,
    priority: str = "medium"
) -> Optional[Dict]:
    """
    Find the best available time slot for a task

    Args:
        available_slots: List of available time slots
        duration_minutes: Required duration in minutes
        preferred_time: User's preferred time (morning/afternoon/evening)
        priority: Task priority (high/medium/low)

    Returns:
        Best matching time slot or None
    """
    suitable_slots = [
        slot for slot in available_slots
        if slot["duration_minutes"] >= duration_minutes
    ]

    if not suitable_slots:
        return None

    # Filter by preferred time if specified
    if preferred_time:
        preferred_slots = []
        for slot in suitable_slots:
            slot_start = datetime.fromisoformat(slot["start"])
            hour = slot_start.hour

            if preferred_time == "morning" and 6 <= hour < 12:
                preferred_slots.append(slot)
            elif preferred_time == "afternoon" and 12 <= hour < 17:
                preferred_slots.append(slot)
            elif preferred_time == "evening" and 17 <= hour < 21:
                preferred_slots.append(slot)

        if preferred_slots:
            suitable_slots = preferred_slots

    # For high priority, prefer earliest slot
    # For low priority, prefer later slot
    if priority == "high":
        return suitable_slots[0]
    elif priority == "low":
        return suitable_slots[-1]
    else:
        # Medium priority - prefer middle slots
        return suitable_slots[len(suitable_slots) // 2]
