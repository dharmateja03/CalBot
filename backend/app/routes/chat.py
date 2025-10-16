"""
Chat routes
Main NL processing endpoint for task scheduling/management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.services.claude_service import TaskParser
from app.services.calendar_service import GoogleCalendarService
from app.services.scheduler_service import TaskScheduler

router = APIRouter()


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


@router.post("", response_model=ChatResponse)
async def process_chat(message: ChatMessage):
    """
    Main chat endpoint - processes natural language input
    Handles: scheduling, editing, deleting tasks via NL

    Examples:
    - "Schedule 2 hours for marketing report tomorrow"
    - "Cancel tomorrow's meeting"
    - "Gym every day for next 10 days at 6am"
    """
    try:
        # Step 1: Parse natural language with OpenAI
        parsed_result = TaskParser.parse_task(message.message)

        if not parsed_result["success"]:
            return ChatResponse(
                reply="I couldn't understand that. Could you please rephrase?",
                success=False
            )

        parsed_data = parsed_result["data"]

        # Step 2: Check if clarification needed
        if parsed_data.get("needs_clarification"):
            return ChatResponse(
                reply="I need some more information:",
                needs_clarification=True,
                clarification_questions=parsed_data.get("clarification_questions", []),
                success=True
            )

        # Step 3: Initialize services
        # TODO: Get actual user credentials from auth
        calendar_service = GoogleCalendarService(user_credentials=None)
        scheduler = TaskScheduler(calendar_service)

        # Step 4: Handle different actions
        action = parsed_data.get("action", "schedule")

        if action == "schedule" and parsed_data.get("tasks"):
            scheduled_tasks = []

            # Get user preferences (TODO: fetch from database)
            user_preferences = {
                "work_hours_start": "09:00",
                "work_hours_end": "17:00",
                "break_start": "12:00",
                "break_end": "13:00",
                "timezone": "UTC"
            }

            # Schedule each parsed task
            for task_data in parsed_data["tasks"]:
                result = scheduler.schedule_task(task_data, user_preferences)

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

                return ChatResponse(
                    reply=reply,
                    scheduled_tasks=scheduled_tasks,
                    success=True
                )
            else:
                return ChatResponse(
                    reply="I couldn't find a suitable time slot. Would you like to see some alternatives?",
                    success=False
                )

        elif action == "cancel":
            # TODO: Implement cancel logic
            return ChatResponse(
                reply="Cancellation feature coming soon!",
                success=True
            )

        elif action == "reschedule":
            # TODO: Implement reschedule logic
            return ChatResponse(
                reply="Rescheduling feature coming soon!",
                success=True
            )

        else:
            return ChatResponse(
                reply="I understand. How can I help you schedule your tasks?",
                success=True
            )

    except Exception as e:
        # Log error (TODO: implement proper logging)
        print(f"Error in chat endpoint: {str(e)}")

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
    # TODO: Delete from database
    return {"message": "Chat history cleared", "success": True}
