"""
Claude Service - Natural Language Task Parsing
Handles all Anthropic Claude API interactions for task understanding
"""

from anthropic import Anthropic
from typing import Dict, List, Optional
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Anthropic client (optional - will return demo data if not configured)
api_key = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key) if api_key else None


class TaskParser:
    """Parse natural language into structured task data"""

    SYSTEM_PROMPT = """You are an AI assistant that helps parse natural language task descriptions into structured data for calendar scheduling.

IMPORTANT: Respond ONLY with valid JSON. No markdown, no code blocks, no explanations.

When the user describes a task, extract:
1. Task title/name
2. Duration in minutes
3. Priority (high, medium, low)
4. Deadline (if mentioned)
5. Preferred time (morning, afternoon, evening, or specific time)
6. Whether it's a recurring task
7. Recurrence pattern (if applicable): daily, weekly, specific days
8. Number of occurrences (for recurring tasks)

For recurring tasks, examples:
- "gym every day for next 10 days" → recurring: true, pattern: "daily", occurrences: 10
- "team meeting every Monday for 4 weeks" → recurring: true, pattern: "weekly_monday", occurrences: 4
- "standup every weekday for 2 weeks" → recurring: true, pattern: "weekdays", occurrences: 10

Respond with this exact JSON structure:
{{
  "action": "schedule",
  "tasks": [
    {{
      "title": "extracted title",
      "duration_minutes": 60,
      "priority": "medium",
      "deadline": null,
      "preferred_time": "afternoon",
      "recurring": false,
      "recurrence_pattern": null,
      "occurrences": null
    }}
  ],
  "needs_clarification": false,
  "clarification_questions": [],
  "confidence": 0.9
}}

Current date/time: {current_datetime}
"""

    @staticmethod
    def parse_task(user_input: str) -> Dict:
        """
        Parse user's natural language input into structured task data

        Args:
            user_input: Natural language task description

        Returns:
            Parsed task data with confidence score
        """
        try:
            # If no Claude API key, return demo response
            if client is None:
                return {
                    "success": True,
                    "data": {
                        "action": "schedule",
                        "tasks": [{
                            "title": "Demo Task",
                            "duration_minutes": 60,
                            "priority": "medium",
                            "deadline": None,
                            "preferred_time": None,
                            "recurring": False,
                            "recurrence_pattern": None,
                            "occurrences": None
                        }],
                        "needs_clarification": False,
                        "clarification_questions": [],
                        "confidence": 0.9
                    },
                    "raw_response": "Demo mode - add ANTHROPIC_API_KEY to .env for real AI parsing"
                }

            current_datetime = datetime.now().isoformat()

            # Call Claude API
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Using Claude 3.5 Sonnet
                max_tokens=1024,
                system=TaskParser.SYSTEM_PROMPT.format(
                    current_datetime=current_datetime
                ),
                messages=[
                    {
                        "role": "user",
                        "content": user_input
                    }
                ]
            )

            # Extract the text content from Claude's response
            response_text = message.content[0].text

            # Clean up response - remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            # Parse the JSON response
            result = json.loads(response_text)

            return {
                "success": True,
                "data": result,
                "raw_response": response_text
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def generate_confirmation_message(task_data: Dict) -> str:
        """Generate a friendly confirmation message for the user"""

        if not task_data.get("success"):
            return "I couldn't understand that. Could you rephrase?"

        data = task_data["data"]
        action = data.get("action", "schedule")

        if action == "schedule" and data.get("tasks"):
            task = data["tasks"][0]
            title = task.get("title", "task")
            duration = task.get("duration_minutes", 0)
            hours = duration // 60
            minutes = duration % 60

            time_str = ""
            if hours > 0:
                time_str = f"{hours} hour{'s' if hours > 1 else ''}"
            if minutes > 0:
                if time_str:
                    time_str += f" and {minutes} minutes"
                else:
                    time_str = f"{minutes} minutes"

            if task.get("recurring"):
                pattern = task.get("recurrence_pattern", "")
                occurrences = task.get("occurrences", 1)
                return f"I'll schedule '{title}' ({time_str}) {pattern} for {occurrences} occurrences."
            else:
                return f"I'll schedule '{title}' for {time_str}."

        return "I understand. Let me process that for you."


class ConversationManager:
    """Manage multi-turn conversations with context"""

    def __init__(self):
        self.conversation_history = []

    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def get_context(self, max_messages: int = 10) -> List[Dict]:
        """Get recent conversation context"""
        return self.conversation_history[-max_messages:]

    def clear(self):
        """Clear conversation history"""
        self.conversation_history = []
