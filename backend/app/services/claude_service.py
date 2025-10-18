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
import pytz

# Load environment variables
load_dotenv()

# Initialize Anthropic client (optional - will return demo data if not configured)
api_key = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key) if api_key else None

# Get timezone from environment
TIMEZONE = os.getenv("TIMEZONE", "UTC")

# Model selection - Use Haiku for cost savings (12x cheaper than Sonnet)
# Haiku: $0.25/$1.25 per 1M tokens (input/output)
# Sonnet: $3/$15 per 1M tokens (input/output)
DEFAULT_MODEL = "claude-3-5-haiku-20241022"  # Cheaper, fast, good quality
ADVANCED_MODEL = "claude-3-5-sonnet-20241022"  # More expensive, best quality


class TaskParser:
    """Parse natural language into structured task data"""

    @staticmethod
    def _choose_model(user_input: str, has_context: bool = False) -> str:
        """
        Choose the appropriate model based on task complexity

        Args:
            user_input: The user's message
            has_context: Whether conversation context exists

        Returns:
            Model name to use
        """
        # Use advanced model for:
        # 1. Very long/complex queries (>100 chars with multiple clauses)
        # 2. Queries with heavy context dependency
        # 3. Recurring pattern parsing

        complex_indicators = [
            "every", "recurring", "repeat", "weekly", "daily", "monthly",
            "and then", "but also", "except when", "unless"
        ]

        is_complex = (
            len(user_input) > 100 or
            any(indicator in user_input.lower() for indicator in complex_indicators) or
            (has_context and len(user_input.split()) > 20)
        )

        if is_complex:
            print(f"🧠 Using {ADVANCED_MODEL} (complex query)")
            return ADVANCED_MODEL
        else:
            print(f"⚡ Using {DEFAULT_MODEL} (simple query - cost optimized)")
            return DEFAULT_MODEL

    SYSTEM_PROMPT = """You are an AI assistant that helps parse natural language task descriptions into structured data for calendar scheduling.

IMPORTANT: Respond ONLY with valid JSON. No markdown, no code blocks, no explanations.

When the user describes a task, extract:
1. Task title/name
2. Duration in minutes (DEFAULT: 60 if not specified)
3. Priority (high, medium, low)
4. Deadline (if mentioned)
5. Preferred time (morning, afternoon, evening, or specific time)
6. Whether it's a recurring task
7. Recurrence pattern (if applicable): daily, weekly, specific days
8. Number of occurrences (for recurring tasks)

IMPORTANT: If duration is NOT mentioned, set duration_minutes to 60 (1 hour default).

For recurring tasks, examples:
- "gym every day for next 10 days" → recurring: true, pattern: "daily", occurrences: 10
- "team meeting every Monday for 4 weeks" → recurring: true, pattern: "weekly_monday", occurrences: 4
- "standup every weekday for 2 weeks" → recurring: true, pattern: "weekdays", occurrences: 10

Special actions:
- If user asks to "summarize my day" or "show me my schedule today", set action to "summarize_day"
- If user asks to "summarize [specific date]" like "summarize 15th October" or "summarize December 25", set action to "summarize_day" and include the date
- If user asks to "summarize this week", set action to "summarize_week"

For summarization actions, include the target_date field:
- "summarize my day" → target_date: null (means today)
- "summarize tomorrow" → target_date: "tomorrow"
- "summarize 15th October" → target_date: "2025-10-15"
- "summarize December 25" → target_date: "2025-12-25"

Respond with this exact JSON structure:
{{
  "action": "schedule",
  "target_date": null,
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
    def parse_task(user_input: str, conversation_history: Optional[List[Dict]] = None, context_summary: Optional[str] = None, user_timezone: Optional[str] = None) -> Dict:
        """
        Parse user's natural language input into structured task data

        Args:
            user_input: Natural language task description
            conversation_history: Recent conversation messages (optional)
            context_summary: Summary of older conversation context (optional)
            user_timezone: User's timezone (optional, overrides env)

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

            # Get current datetime in the user's timezone
            tz_name = user_timezone or TIMEZONE
            tz = pytz.timezone(tz_name)
            current_datetime = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

            # Build system prompt with optional context summary
            system_prompt = TaskParser.SYSTEM_PROMPT.format(current_datetime=current_datetime)

            if context_summary:
                system_prompt = f"""Previous conversation summary:
{context_summary}

{system_prompt}"""

            # Build messages array with conversation history
            messages = []

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add current user message
            messages.append({
                "role": "user",
                "content": user_input
            })

            # Choose appropriate model based on complexity
            model = TaskParser._choose_model(user_input, has_context=bool(conversation_history))

            # Call Claude API with conversation context
            message = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages
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

    def __init__(self, max_history: int = 20):
        """
        Initialize conversation manager

        Args:
            max_history: Maximum number of messages to keep in memory
        """
        self.conversation_history = []
        self.max_history = max_history
        self.summarized_context = None

    def add_message(self, role: str, content: str):
        """
        Add a message to conversation history

        Args:
            role: 'user' or 'assistant'
            content: Message content
        """
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Auto-summarize if history gets too long
        if len(self.conversation_history) > self.max_history:
            self._summarize_old_context()

    def get_context(self, max_messages: int = 10) -> List[Dict]:
        """
        Get recent conversation context in Claude API format

        Args:
            max_messages: Number of recent messages to include

        Returns:
            List of message dicts for Claude API
        """
        recent_messages = self.conversation_history[-max_messages:]

        # Convert to Claude API format (remove timestamp)
        formatted_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in recent_messages
        ]

        return formatted_messages

    def get_context_with_summary(self, recent_count: int = 6) -> tuple[Optional[str], List[Dict]]:
        """
        Get both summarized old context and recent messages

        Args:
            recent_count: Number of recent messages to include

        Returns:
            Tuple of (summary_text, recent_messages)
        """
        recent_messages = self.get_context(max_messages=recent_count)
        return (self.summarized_context, recent_messages)

    def _summarize_old_context(self):
        """
        Summarize old messages to save context window
        Uses Claude to create a summary of older conversations
        """
        if len(self.conversation_history) <= 10:
            return

        # Keep last 10 messages, summarize the rest
        old_messages = self.conversation_history[:-10]

        if not client:
            # No API available, just truncate
            self.conversation_history = self.conversation_history[-10:]
            return

        try:
            # Create summary of old messages
            summary_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in old_messages
            ])

            summary_prompt = f"""Summarize this conversation history concisely, focusing on:
- Tasks scheduled and their details
- User preferences mentioned
- Important context for future interactions

Conversation:
{summary_text}

Provide a brief 2-3 sentence summary."""

            # Use cheaper model for summarization (simple task)
            print(f"📝 Using {DEFAULT_MODEL} for conversation summarization (cost optimized)")

            message = client.messages.create(
                model=DEFAULT_MODEL,  # Use Haiku for cost savings
                max_tokens=200,
                messages=[{"role": "user", "content": summary_prompt}]
            )

            self.summarized_context = message.content[0].text

            # Keep only recent messages
            self.conversation_history = self.conversation_history[-10:]

            print(f"📝 Summarized {len(old_messages)} old messages")

        except Exception as e:
            print(f"Failed to summarize context: {e}")
            # Fallback: just truncate
            self.conversation_history = self.conversation_history[-10:]

    def clear(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.summarized_context = None
