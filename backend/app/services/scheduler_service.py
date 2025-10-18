"""
Scheduler Service
Handles task scheduling logic and recurring task generation
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.services.calendar_service import GoogleCalendarService, find_best_time_slot
import pytz
import os


class TaskScheduler:
    """Intelligent task scheduling engine"""

    def __init__(self, calendar_service: GoogleCalendarService):
        """
        Initialize scheduler with calendar service

        Args:
            calendar_service: Google Calendar service instance
        """
        self.calendar = calendar_service

    def schedule_task(
        self,
        task_data: Dict,
        user_preferences: Optional[Dict] = None,
        user_timezone: Optional[str] = None
    ) -> Dict:
        """
        Schedule a single task or generate recurring tasks

        Args:
            task_data: Parsed task information
            user_preferences: User's scheduling preferences
            user_timezone: User's timezone (optional, overrides preferences)

        Returns:
            Scheduling result with created events
        """
        # Default preferences
        if not user_preferences:
            user_preferences = {
                "work_hours_start": "09:00",
                "work_hours_end": "17:00",
                "break_start": "12:00",
                "break_end": "13:00",
                "timezone": user_timezone or "UTC"
            }
        elif user_timezone:
            # Override timezone from preferences with user_timezone if provided
            user_preferences["timezone"] = user_timezone

        # Check if recurring
        if task_data.get("recurring"):
            return self._schedule_recurring_task(task_data, user_preferences, user_timezone)
        else:
            return self._schedule_single_task(task_data, user_preferences, user_timezone)

    def _schedule_single_task(
        self,
        task_data: Dict,
        user_preferences: Dict,
        user_timezone: Optional[str] = None
    ) -> Dict:
        """Schedule a single non-recurring task"""

        title = task_data.get("title", "Untitled Task")
        duration = task_data.get("duration_minutes", 60)
        priority = task_data.get("priority", "medium")
        preferred_time = task_data.get("preferred_time")
        deadline = task_data.get("deadline")

        # Check if user specified exact start and end times
        # Claude may put start time in preferred_time and end time in deadline
        print(f"DEBUG: preferred_time='{preferred_time}', deadline='{deadline}'")
        if preferred_time and deadline:
            try:
                # Try to parse deadline as full ISO timestamp
                end_time = datetime.fromisoformat(deadline)
                print(f"DEBUG: Parsed end_time: {end_time}")

                # Try to parse preferred_time
                # It could be a full ISO timestamp or just a time like "13:00"
                try:
                    start_time = datetime.fromisoformat(preferred_time)
                    print(f"DEBUG: Parsed preferred_time as ISO: {start_time}")
                except ValueError as ve:
                    print(f"DEBUG: preferred_time not ISO, trying as time: {preferred_time}")
                    # Parse time in various formats: "13:00", "1pm", "1:30pm", etc.
                    time_str = str(preferred_time).lower().strip()

                    # Check for am/pm format
                    is_pm = 'pm' in time_str
                    is_am = 'am' in time_str
                    time_str = time_str.replace('am', '').replace('pm', '').strip()

                    # Parse hour and minute
                    if ":" in time_str:
                        time_parts = time_str.split(":")
                        hour = int(time_parts[0])
                        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    else:
                        # Just a number like "1" or "13"
                        hour = int(time_str)
                        minute = 0

                    # Convert to 24-hour format if pm/am specified
                    if is_pm and hour < 12:
                        hour += 12
                    elif is_am and hour == 12:
                        hour = 0

                    print(f"DEBUG: Parsed hour={hour}, minute={minute}")
                    start_time = datetime.combine(
                        end_time.date(),
                        datetime.min.time().replace(hour=hour, minute=minute)
                    )
                    print(f"DEBUG: Combined start_time: {start_time}")

                # If we successfully parsed both times, schedule at exact time
                if isinstance(start_time, datetime) and isinstance(end_time, datetime):
                    print(f"DEBUG: Scheduling exact time: {start_time} to {end_time}")
                    event = self.calendar.create_event(
                        title=title,
                        start_time=start_time,
                        end_time=end_time,
                        description=f"Priority: {priority}\nScheduled by CalBot"
                    )

                    return {
                        "success": True,
                        "event": event,
                        "message": f"Scheduled '{title}' for {start_time.strftime('%b %d at %I:%M %p')}"
                    }
            except (ValueError, TypeError) as e:
                # Not exact timestamps, fall through to normal scheduling
                print(f"DEBUG: Could not parse exact times: {e}")
                import traceback
                traceback.print_exc()
                pass

        # Determine search range for finding available slots
        # Use timezone-aware datetime from user's browser
        tz_name = user_timezone or user_preferences.get("timezone") or os.getenv("TIMEZONE", "UTC")
        tz = pytz.timezone(tz_name)
        start_date = datetime.now(tz)
        if deadline:
            try:
                end_date = datetime.fromisoformat(deadline)
                # Make timezone-aware if it isn't already
                if end_date.tzinfo is None:
                    end_date = tz.localize(end_date)
            except:
                end_date = start_date + timedelta(days=7)
        else:
            end_date = start_date + timedelta(days=7)

        # Get available slots
        available_slots = self.calendar.get_availability(
            start_date,
            end_date,
            user_preferences["work_hours_start"],
            user_preferences["work_hours_end"]
        )

        # Find best slot
        best_slot = find_best_time_slot(
            available_slots,
            duration,
            preferred_time,
            priority
        )

        if not best_slot:
            return {
                "success": False,
                "error": "No available time slots found",
                "alternatives": available_slots[:3]  # Suggest first 3 slots
            }

        # Calculate end time
        start_time = datetime.fromisoformat(best_slot["start"])
        end_time = start_time + timedelta(minutes=duration)

        # Create calendar event
        event = self.calendar.create_event(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=f"Priority: {priority}\nScheduled by CalBot"
        )

        return {
            "success": True,
            "event": event,
            "message": f"Scheduled '{title}' for {start_time.strftime('%b %d at %I:%M %p')}"
        }

    def _schedule_recurring_task(
        self,
        task_data: Dict,
        user_preferences: Dict,
        user_timezone: Optional[str] = None
    ) -> Dict:
        """Schedule recurring tasks"""

        title = task_data.get("title", "Untitled Task")
        duration = task_data.get("duration_minutes", 60)
        pattern = task_data.get("recurrence_pattern", "daily")
        occurrences = task_data.get("occurrences", 1)
        preferred_time = task_data.get("preferred_time")

        events_created = []
        # Use timezone-aware datetime from user's browser
        tz_name = user_timezone or user_preferences.get("timezone") or os.getenv("TIMEZONE", "UTC")
        tz = pytz.timezone(tz_name)
        start_date = datetime.now(tz)

        # Generate occurrence dates based on pattern
        occurrence_dates = self._generate_occurrence_dates(
            start_date,
            pattern,
            occurrences
        )

        # Schedule each occurrence
        for occurrence_date in occurrence_dates:
            # Get availability for that day
            day_start = datetime.combine(
                occurrence_date.date(),
                datetime.strptime(user_preferences["work_hours_start"], "%H:%M").time()
            )
            day_end = datetime.combine(
                occurrence_date.date(),
                datetime.strptime(user_preferences["work_hours_end"], "%H:%M").time()
            )

            available_slots = self.calendar.get_availability(
                day_start,
                day_end,
                user_preferences["work_hours_start"],
                user_preferences["work_hours_end"]
            )

            # Find slot for this occurrence
            best_slot = find_best_time_slot(
                available_slots,
                duration,
                preferred_time,
                "medium"
            )

            if best_slot:
                start_time = datetime.fromisoformat(best_slot["start"])
                end_time = start_time + timedelta(minutes=duration)

                event = self.calendar.create_event(
                    title=title,
                    start_time=start_time,
                    end_time=end_time,
                    description=f"Recurring task ({pattern})\nScheduled by CalBot"
                )

                events_created.append(event)

        if not events_created:
            return {
                "success": False,
                "error": "Could not schedule any occurrences",
                "attempted": occurrences
            }

        return {
            "success": True,
            "events": events_created,
            "message": f"Scheduled {len(events_created)} occurrences of '{title}'"
        }

    def _generate_occurrence_dates(
        self,
        start_date: datetime,
        pattern: str,
        count: int
    ) -> List[datetime]:
        """
        Generate dates for recurring tasks

        Args:
            start_date: Starting date
            pattern: Recurrence pattern (daily, weekly_monday, weekdays, etc.)
            count: Number of occurrences

        Returns:
            List of datetime objects for each occurrence
        """
        dates = []
        current_date = start_date

        if pattern == "daily":
            # Every day
            for i in range(count):
                dates.append(current_date + timedelta(days=i))

        elif pattern == "weekdays":
            # Monday through Friday only
            while len(dates) < count:
                if current_date.weekday() < 5:  # 0-4 = Mon-Fri
                    dates.append(current_date)
                current_date += timedelta(days=1)

        elif pattern.startswith("weekly_"):
            # Specific day of week (e.g., weekly_monday)
            day_name = pattern.split("_")[1]
            day_mapping = {
                "monday": 0, "tuesday": 1, "wednesday": 2,
                "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
            }
            target_day = day_mapping.get(day_name, 0)

            # Find next occurrence of that day
            days_ahead = target_day - current_date.weekday()
            if days_ahead <= 0:
                days_ahead += 7

            first_occurrence = current_date + timedelta(days=days_ahead)

            for i in range(count):
                dates.append(first_occurrence + timedelta(weeks=i))

        else:
            # Default to daily
            for i in range(count):
                dates.append(current_date + timedelta(days=i))

        return dates


def reschedule_task(
    calendar_service: GoogleCalendarService,
    event_id: str,
    new_start_time: Optional[datetime] = None,
    duration_minutes: Optional[int] = None
) -> Dict:
    """
    Reschedule an existing task

    Args:
        calendar_service: Calendar service instance
        event_id: Event ID to reschedule
        new_start_time: New start time (optional)
        duration_minutes: New duration (optional)

    Returns:
        Updated event data
    """
    # TODO: Implement rescheduling logic
    pass


def cancel_task(
    calendar_service: GoogleCalendarService,
    event_id: str
) -> bool:
    """
    Cancel/delete a scheduled task

    Args:
        calendar_service: Calendar service instance
        event_id: Event ID to cancel

    Returns:
        True if successful
    """
    return calendar_service.delete_event(event_id)
