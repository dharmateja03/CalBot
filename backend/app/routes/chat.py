"""
Chat routes
Main NL processing endpoint for task scheduling/management
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import httpx

from app.services.claude_service import TaskParser, ConversationManager
from app.services.calendar_service import GoogleCalendarService
from app.services.scheduler_service import TaskScheduler

router = APIRouter()

# In-memory conversation storage per user
# TODO: Replace with database storage for production
user_conversations = {}


class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "demo_user"  # TODO: Get from auth


class ScheduledTask(BaseModel):
    title: str
    start: str
    end: str
    calendar_event_id: str
    description: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    scheduled_tasks: List[ScheduledTask] = []
    needs_clarification: bool = False
    clarification_questions: List[str] = []
    success: bool = True


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
        # Get user timezone from header or default to env/UTC
        import os
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
                return create_response(
                    f"📅 You have no events scheduled for {date_display}. That day is completely free!",
                    success=True
                )

            # Format events summary
            summary_lines = [f"📅 Here's your schedule for {date_display}:\n"]
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
                if len(scheduled_tasks) == 1:
                    task = scheduled_tasks[0]
                    start_time = datetime.fromisoformat(task.start)
                    reply = f"✅ Scheduled '{task.title}' for {start_time.strftime('%A, %B %d at %I:%M %p')}"
                else:
                    reply = f"✅ Scheduled {len(scheduled_tasks)} occurrences of '{scheduled_tasks[0].title}'"

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
            # TODO: Implement cancel logic
            return create_response(
                "Cancellation feature coming soon!",
                success=True
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
        print(f"Error in chat endpoint: {str(e)}")

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
