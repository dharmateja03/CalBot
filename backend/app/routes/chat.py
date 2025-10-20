"""
Chat routes
Main NL processing endpoint for task scheduling/management
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import httpx
import os
import jwt

from app.services.claude_service import TaskParser, ConversationManager
from app.services.calendar_service import GoogleCalendarService
from app.services.scheduler_service import TaskScheduler

# JWT Configuration (same as auth.py)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = "HS256"

router = APIRouter()

# In-memory conversation storage per user
# TODO: Replace with database storage for production
user_conversations = {}

# In-memory pending confirmations storage
# Format: {user_id: {"task_data": {...}, "user_preferences": {...}, "user_timezone": "..."}}
pending_confirmations = {}


class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "demo_user"  # TODO: Get from auth


class ScheduledTask(BaseModel):
    title: str
    start: str
    end: str
    calendar_event_id: str
    description: Optional[str] = None


class ConflictInfo(BaseModel):
    title: str
    start: str
    end: str
    event_id: str


class ChatResponse(BaseModel):
    reply: str
    scheduled_tasks: List[ScheduledTask] = []
    needs_clarification: bool = False
    clarification_questions: List[str] = []
    success: bool = True
    has_conflict: bool = False
    conflicts: List[ConflictInfo] = []
    proposed_event: Optional[ScheduledTask] = None


def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_username_from_email(email: str) -> str:
    """Extract username from email address"""
    username = email.split('@')[0]
    return username.capitalize()


async def get_user_credentials(user_id: str) -> Optional[dict]:
    """
    Fetch user's Google OAuth tokens from auth service

    Args:
        user_id: User ID to fetch tokens for

    Returns:
        Dict with OAuth credentials or None if not found
    """
    try:
        # Call auth service to get user tokens
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:8000/auth/tokens/{user_id}")
            if response.status_code == 200:
                return response.json()
            else:
                return None
    except Exception as e:
        print(f"⚠️  Failed to fetch user credentials: {e}")
        return None


@router.post("", response_model=ChatResponse)
async def process_chat(
    message: ChatMessage,
    authorization: Optional[str] = Header(None),
    x_timezone: Optional[str] = Header(None, alias="X-Timezone")
):
    """
    Main chat endpoint - processes natural language input with conversation memory
    Handles: scheduling, editing, deleting tasks via NL

    Examples:
    - "Schedule 2 hours for marketing report tomorrow"
    - "Cancel tomorrow's meeting"
    - "Gym every day for next 10 days at 6am"
    - "What did I schedule yesterday?" (uses conversation memory)
    """
    try:
        # Get username from JWT token
        username = None
        user_email = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "")
            payload = verify_jwt_token(token)
            if payload and "email" in payload:
                user_email = payload["email"]
                username = get_username_from_email(user_email)
                print(f"👤 User: {username} ({user_email})")

        # Get user timezone from header or default to env/UTC
        user_timezone = x_timezone or os.getenv("TIMEZONE", "UTC")
        print(f"🌍 Using timezone: {user_timezone} (from {'header' if x_timezone else 'env'})")

        # Get or create conversation manager for this user
        user_id = message.user_id
        if user_id not in user_conversations:
            user_conversations[user_id] = ConversationManager(max_history=20)

        conversation = user_conversations[user_id]

        # Get conversation context (summary + recent messages)
        context_summary, recent_messages = conversation.get_context_with_summary(recent_count=6)

        # Step 1: Parse natural language with Claude (with conversation context and timezone)
        parsed_result = TaskParser.parse_task(
            message.message,
            conversation_history=recent_messages,
            context_summary=context_summary,
            user_timezone=user_timezone
        )

        # Add user message to conversation history
        conversation.add_message("user", message.message)

        # Helper function to add assistant response and return
        def create_response(reply: str, **kwargs) -> ChatResponse:
            """Helper to add assistant message to conversation and create response"""
            conversation.add_message("assistant", reply)
            return ChatResponse(reply=reply, **kwargs)

        # Check if user is confirming a pending conflict
        user_message_lower = message.message.lower().strip()
        if user_id in pending_confirmations and user_message_lower in ["yes", "y", "sure", "ok", "okay", "yeah", "yep"]:
            # User confirmed - force schedule the conflicting event
            pending = pending_confirmations[user_id]
            task_data = pending["task_data"]
            user_preferences = pending["user_preferences"]
            user_tz = pending["user_timezone"]

            # Initialize services
            user_credentials = await get_user_credentials(user_id)
            if user_credentials:
                calendar_service = GoogleCalendarService(
                    user_id=user_id,
                    credentials_dict=user_credentials
                )
            else:
                calendar_service = GoogleCalendarService()

            scheduler = TaskScheduler(calendar_service)

            # Force schedule by creating event directly (bypass conflict check)
            import pytz

            title = task_data.get("title", "Untitled Task")
            duration = task_data.get("duration_minutes", 60)
            priority = task_data.get("priority", "medium")

            # Get start time from pending confirmation
            if "start_time" in pending:
                start_time = datetime.fromisoformat(pending["start_time"])
                end_time = datetime.fromisoformat(pending["end_time"])
            else:
                # Fallback - shouldn't happen
                tz = pytz.timezone(user_tz)
                start_time = datetime.now(tz)
                end_time = start_time + timedelta(minutes=duration)

            # Create the event
            event = calendar_service.create_event(
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=f"Priority: {priority}\\nScheduled by CalBot"
            )

            # Clear pending confirmation
            del pending_confirmations[user_id]

            # Return success
            greeting = f"Great, {username}! " if username else ""
            scheduled_task = ScheduledTask(
                title=event["title"],
                start=event["start"],
                end=event["end"],
                calendar_event_id=event["id"],
                description=event.get("description")
            )

            return create_response(
                f"{greeting}✅ Scheduled '{title}' for {start_time.strftime('%A, %B %d at %I:%M %p')} (even though there's a conflict)",
                scheduled_tasks=[scheduled_task],
                success=True
            )

        if not parsed_result["success"]:
            return create_response(
                "I couldn't understand that. Could you please rephrase?",
                success=False
            )

        parsed_data = parsed_result["data"]

        # Step 2: Check if clarification needed
        if parsed_data.get("needs_clarification"):
            return create_response(
                "I need some more information:",
                needs_clarification=True,
                clarification_questions=parsed_data.get("clarification_questions", []),
                success=True
            )

        # Step 3: Initialize services with user credentials
        # Try to get user's OAuth tokens for real calendar access
        user_credentials = await get_user_credentials(user_id)

        if user_credentials:
            calendar_service = GoogleCalendarService(
                user_id=user_id,
                credentials_dict=user_credentials
            )
            print(f"✅ Using real Google Calendar for user: {user_id}")
        else:
            # Fallback to mock mode if no credentials
            calendar_service = GoogleCalendarService()
            print(f"⚠️  No credentials for user {user_id}, using mock calendar")

        scheduler = TaskScheduler(calendar_service)

        # Step 4: Handle different actions
        action = parsed_data.get("action", "schedule")

        if action == "summarize_day":
            # Parse target date if provided
            target_date_str = parsed_data.get("target_date")

            if target_date_str and target_date_str != "null":
                # Handle different date formats
                try:
                    if target_date_str.lower() == "tomorrow":
                        target_date = datetime.now() + timedelta(days=1)
                    elif target_date_str.lower() == "yesterday":
                        target_date = datetime.now() - timedelta(days=1)
                    else:
                        # Try parsing ISO format (YYYY-MM-DD)
                        target_date = datetime.fromisoformat(target_date_str)
                except:
                    # If parsing fails, default to today
                    target_date = datetime.now()
            else:
                # Default to today
                target_date = datetime.now()

            # Get events for the target date
            day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start.replace(hour=23, minute=59, second=59)

            events = calendar_service.get_events(day_start, day_end)

            # Format the date for display
            if target_date.date() == datetime.now().date():
                date_display = "today"
            elif target_date.date() == (datetime.now() + timedelta(days=1)).date():
                date_display = "tomorrow"
            elif target_date.date() == (datetime.now() - timedelta(days=1)).date():
                date_display = "yesterday"
            else:
                date_display = f"on {target_date.strftime('%A, %B %d, %Y')}"

            if not events:
                greeting = f"{username}, you" if username else "You"
                return create_response(
                    f"📅 {greeting} have no events scheduled for {date_display}. That day is completely free!",
                    success=True
                )

            # Format events summary
            greeting_prefix = f"{username}, here's" if username else "Here's"
            summary_lines = [f"📅 {greeting_prefix} your schedule for {date_display}:\n"]
            for event in events:
                start_time = datetime.fromisoformat(event["start"])
                end_time = datetime.fromisoformat(event["end"])
                duration = (end_time - start_time).total_seconds() / 60
                hours = int(duration // 60)
                minutes = int(duration % 60)

                time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                summary_lines.append(
                    f"• {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}: "
                    f"{event['title']} ({time_str})"
                )

            return create_response(
                "\n".join(summary_lines),
                success=True
            )

        elif action == "summarize_week":
            # Get this week's events
            week_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = week_start - timedelta(days=week_start.weekday())  # Start from Monday
            week_end = week_start + timedelta(days=7)

            events = calendar_service.get_events(week_start, week_end)

            if not events:
                return create_response(
                    "📅 You have no events scheduled for this week.",
                    success=True
                )

            # Group events by day
            events_by_day = {}
            for event in events:
                start_time = datetime.fromisoformat(event["start"])
                day_key = start_time.strftime('%A, %B %d')
                if day_key not in events_by_day:
                    events_by_day[day_key] = []
                events_by_day[day_key].append(event)

            # Format week summary
            summary_lines = ["📅 Here's your week summary:\n"]
            for day, day_events in sorted(events_by_day.items()):
                summary_lines.append(f"\n**{day}**")
                for event in day_events:
                    start_time = datetime.fromisoformat(event["start"])
                    end_time = datetime.fromisoformat(event["end"])
                    summary_lines.append(
                        f"  • {start_time.strftime('%I:%M %p')}: {event['title']}"
                    )

            return create_response(
                "\n".join(summary_lines),
                success=True
            )

        elif action == "decompose_and_schedule":
            # Handle task decomposition - schedule all subtasks
            subtasks = parsed_data.get("subtasks", [])
            original_task = parsed_data.get("original_task", "")
            message = parsed_data.get("message", "")
            reasoning = parsed_data.get("reasoning", "")

            if not subtasks:
                return create_response(
                    "I couldn't break down that task. Could you provide more details?",
                    success=False
                )

            # Get user preferences
            user_preferences = {
                "work_hours_start": "09:00",
                "work_hours_end": "17:00",
                "break_start": "12:00",
                "break_end": "13:00",
                "timezone": user_timezone
            }

            scheduled_tasks = []

            # Schedule each subtask
            for subtask in sorted(subtasks, key=lambda x: x.get("order", 0)):
                # Map suggested_time to preferred_time
                suggested_time = subtask.get("suggested_time", "morning")

                task_data = {
                    "title": subtask["title"],
                    "duration_minutes": subtask.get("duration_minutes", 60),
                    "priority": subtask.get("priority", "high"),
                    "preferred_time": suggested_time,
                    "description": subtask.get("description", "")
                }

                result = scheduler.schedule_task(task_data, user_preferences, user_timezone)

                if result["success"] and "event" in result:
                    event = result["event"]
                    scheduled_tasks.append(ScheduledTask(
                        title=event["title"],
                        start=event["start"],
                        end=event["end"],
                        calendar_event_id=event["id"],
                        description=event.get("description")
                    ))

            if scheduled_tasks:
                greeting = f"{username}, " if username else ""
                task_list = "\n".join([
                    f"  {i+1}. {task.title} - {datetime.fromisoformat(task.start).strftime('%a %I:%M %p')}"
                    for i, task in enumerate(scheduled_tasks)
                ])

                reply = f"""{greeting}I've broken down "{original_task}" into {len(scheduled_tasks)} manageable chunks:

{task_list}

{message}
{reasoning if reasoning else ''}

All set! 🎯"""

                return create_response(
                    reply,
                    scheduled_tasks=scheduled_tasks,
                    success=True
                )
            else:
                return create_response(
                    "I couldn't schedule the subtasks. Let me try a different approach.",
                    success=False
                )

        elif action == "schedule" and parsed_data.get("tasks"):
            scheduled_tasks = []

            # Get user preferences (TODO: fetch from database)
            user_preferences = {
                "work_hours_start": "09:00",
                "work_hours_end": "17:00",
                "break_start": "12:00",
                "break_end": "13:00",
                "timezone": user_timezone  # Use detected timezone from browser
            }

            # Schedule each parsed task
            for task_data in parsed_data["tasks"]:
                result = scheduler.schedule_task(task_data, user_preferences, user_timezone)

                # Handle conflicts
                if result.get("has_conflict"):
                    # Store pending confirmation for this user
                    proposed = result.get("proposed_event", {})
                    pending_confirmations[user_id] = {
                        "task_data": task_data,
                        "user_preferences": user_preferences,
                        "user_timezone": user_timezone,
                        "start_time": proposed.get("start_time", ""),
                        "end_time": proposed.get("end_time", "")
                    }

                    # Return conflict information to frontend for user confirmation
                    conflict_infos = []
                    for conflict in result.get("conflicts", []):
                        conflict_infos.append(ConflictInfo(
                            title=conflict["title"],
                            start=conflict["start"],
                            end=conflict["end"],
                            event_id=conflict["id"]
                        ))

                    # Create proposed event info
                    proposed_task = ScheduledTask(
                        title=proposed.get("title", ""),
                        start=proposed.get("start_time", ""),
                        end=proposed.get("end_time", ""),
                        calendar_event_id="",  # Not created yet
                        description=""
                    )

                    greeting = f"{username}, " if username else ""
                    return create_response(
                        result.get("message", "Time conflict detected"),
                        success=False,
                        has_conflict=True,
                        conflicts=conflict_infos,
                        proposed_event=proposed_task
                    )

                if result["success"]:
                    if "events" in result:  # Recurring tasks
                        for event in result["events"]:
                            scheduled_tasks.append(ScheduledTask(
                                title=event["title"],
                                start=event["start"],
                                end=event["end"],
                                calendar_event_id=event["id"],
                                description=event.get("description")
                            ))
                    elif "event" in result:  # Single task
                        event = result["event"]
                        scheduled_tasks.append(ScheduledTask(
                            title=event["title"],
                            start=event["start"],
                            end=event["end"],
                            calendar_event_id=event["id"],
                            description=event.get("description")
                        ))

            # Generate confirmation message
            if scheduled_tasks:
                # Add personalized prefix if we have username
                greeting = f"Great, {username}! " if username else ""

                if len(scheduled_tasks) == 1:
                    task = scheduled_tasks[0]
                    start_time = datetime.fromisoformat(task.start)
                    reply = f"{greeting}✅ Scheduled '{task.title}' for {start_time.strftime('%A, %B %d at %I:%M %p')}"
                else:
                    reply = f"{greeting}✅ Scheduled {len(scheduled_tasks)} occurrences of '{scheduled_tasks[0].title}'"

                return create_response(
                    reply,
                    scheduled_tasks=scheduled_tasks,
                    success=True
                )
            else:
                return create_response(
                    "I couldn't find a suitable time slot. Would you like to see some alternatives?",
                    success=False
                )

        elif action == "cancel":
            # Implement cancellation logic
            if not parsed_data.get("tasks") or len(parsed_data["tasks"]) == 0:
                return create_response(
                    "I couldn't identify which event you want to cancel. Could you be more specific?",
                    success=False
                )

            task_to_cancel = parsed_data["tasks"][0]
            title = task_to_cancel.get("title", "")
            preferred_time = task_to_cancel.get("preferred_time")
            deadline = task_to_cancel.get("deadline")

            # Get today's events to search for matching event
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            # If deadline specified, use that as the search date
            if deadline:
                try:
                    deadline_date = datetime.fromisoformat(deadline) if isinstance(deadline, str) else deadline
                    today_start = deadline_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    today_end = today_start + timedelta(days=1)
                except:
                    pass

            events = calendar_service.get_events(today_start, today_end)

            # Find matching event
            matched_event = None
            for event in events:
                event_title_lower = event.get("title", "").lower()
                search_title_lower = title.lower()

                # Check if titles match (fuzzy matching)
                if search_title_lower in event_title_lower or event_title_lower in search_title_lower:
                    # If time specified, also check time
                    if preferred_time:
                        event_start = datetime.fromisoformat(event["start"])
                        event_hour = event_start.hour

                        # Parse preferred time
                        time_str = str(preferred_time).lower().strip()
                        is_pm = 'pm' in time_str
                        is_am = 'am' in time_str
                        time_str = time_str.replace('am', '').replace('pm', '').replace(':', '').strip()

                        try:
                            search_hour = int(time_str)
                            if is_pm and search_hour < 12:
                                search_hour += 12
                            elif is_am and search_hour == 12:
                                search_hour = 0

                            # Check if hours match
                            if event_hour == search_hour:
                                matched_event = event
                                break
                        except:
                            # If can't parse time, just use title match
                            matched_event = event
                            break
                    else:
                        matched_event = event
                        break

            if not matched_event:
                return create_response(
                    f"I couldn't find an event matching '{title}'{' at ' + preferred_time if preferred_time else ''}. Please check your calendar.",
                    success=False
                )

            # Delete the event
            try:
                result = calendar_service.delete_event(matched_event["id"])
                greeting = f"Done, {username}! " if username else ""
                event_time = datetime.fromisoformat(matched_event["start"]).strftime('%I:%M %p')
                return create_response(
                    f"{greeting}✅ Cancelled '{matched_event['title']}' at {event_time}.",
                    success=True
                )
            except Exception as e:
                return create_response(
                    f"I found the event but couldn't cancel it. Error: {str(e)}",
                    success=False
                )

        elif action == "reschedule":
            # TODO: Implement reschedule logic
            return create_response(
                "Rescheduling feature coming soon!",
                success=True
            )

        else:
            return create_response(
                "I understand. How can I help you schedule your tasks?",
                success=True
            )

    except Exception as e:
        # Log error (TODO: implement proper logging)
        print(f"❌ Error in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()

        # Still add error to conversation history if conversation exists
        if message.user_id in user_conversations:
            user_conversations[message.user_id].add_message(
                "assistant",
                "Something went wrong. Please try again."
            )

        return ChatResponse(
            reply="Something went wrong. Please try again.",
            success=False
        )


@router.get("/history")
async def get_chat_history(user_id: str = "demo_user"):
    """Get last 5 days of chat history"""
    # TODO: Fetch from database
    # TODO: Filter last 5 days
    return {
        "messages": [],
        "count": 0
    }


@router.delete("/history")
async def clear_chat_history(user_id: str = "demo_user"):
    """Clear chat history for current user"""
    if user_id in user_conversations:
        user_conversations[user_id].clear()
        print(f"🗑️  Cleared conversation history for user: {user_id}")

    # TODO: Also delete from database when implemented
    return {"message": "Chat history cleared", "success": True}
