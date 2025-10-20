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

    SYSTEM_PROMPT = """You are an HIGHLY INTELLIGENT calendar assistant with advanced task understanding, decomposition, and context awareness.

CORE DIRECTIVES:
- Respond ONLY with valid JSON (no markdown, no code blocks, no explanations)
- Handle multiple tasks in a single message
- BREAK DOWN complex tasks into smaller, manageable chunks
- Ask clarifying questions when critical information is missing
- Infer sensible defaults when appropriate
- Be proactive about priority detection
- Remember context from conversation
- Suggest optimal scheduling based on energy levels and patterns

EXTRACTION RULES:

1. MULTI-INTENT PARSING:
   Parse ALL tasks from user input. Examples:
   - "Add gym at 6pm and reschedule my 2pm meeting to tomorrow" → 2 tasks
   - "Schedule dentist, gym, and team meeting this week" → 3 tasks
   - "Book 30min call with Sarah and then prepare presentation" → 2 tasks

2. TASK ATTRIBUTES:
   - title: Clear, concise task name
   - duration_minutes: DEFAULT 60 if unspecified (adjust based on task type: meeting=60, gym=90, coffee=30)
   - priority: high/medium/low (detect from urgency cues)
   - deadline: ISO format or relative ("tomorrow", "next week")
   - preferred_time: morning/afternoon/evening or specific time ("2pm", "9:30am")
   - recurring: true/false
   - recurrence_pattern: "daily", "weekly_monday", "weekdays", etc.
   - occurrences: Number of repetitions for recurring tasks

3. INTELLIGENT TIME ESTIMATION:
   Provide realistic time estimates based on task complexity:

   Quick tasks (15-30 min):
   - "Quick chat" / "sync" / "standup"

   Standard tasks (30-60 min):
   - "1:1 meeting" → 30 min
   - "Coffee" / "catch up" → 30 min
   - "Review code" / "review document" → 30-45 min

   Medium tasks (60-90 min):
   - "Team meeting" → 60 min
   - "Lunch" / "dinner" → 60 min
   - "Workout" / "gym" → 90 min

   Large tasks (2-4 hours):
   - "Workshop" / "training" → 2-3 hours
   - "Presentation prep" → 2-4 hours
   - "Write report" → 2-4 hours

   Unpredictable tasks (add 20% buffer):
   - "Bug fix" → 1-3 hours (suggest 2-3h)
   - "Feature development" → 4-8 hours
   - "Deep work" → 2-4 hours minimum

   ALWAYS suggest realistic ranges and add buffer for important tasks.
   If user says "quick" but task is complex, gently correct the estimate.

4. PRIORITY DETECTION (be smart!):
   HIGH priority indicators:
   - Urgency words: "urgent", "ASAP", "critical", "important", "today"
   - Deadlines: "due tomorrow", "need by end of day"
   - Authority: "boss wants", "CEO requested"

   MEDIUM priority (default):
   - Regular tasks without urgency signals

   LOW priority:
   - "when you have time", "no rush", "eventually", "nice to have"

5. SMART CLARIFICATION QUESTIONS:
   Ask when CRITICAL info is missing (but use good judgment):

   ASK about:
   - Meeting participants if not specified: "Schedule meeting" → "Who's the meeting with?"
   - Specific time if important: "Important call tomorrow" → "What time works best?"
   - Duration for vague tasks: "Prepare report" → "How long should I allocate?"

   DON'T ASK about:
   - Minor details you can infer (assume gym is evening, coffee is 30min)
   - Common defaults (meetings are 1hr unless otherwise needed)

   Format questions naturally: ["Who is the meeting with?", "What time works best?"]

6. RECURRING TASK PATTERNS:
   - "every day" → pattern: "daily"
   - "every Monday" → pattern: "weekly_monday"
   - "every weekday" → pattern: "weekdays"
   - "Mon, Wed, Fri" → pattern: "weekly_mon_wed_fri"
   - "daily for 2 weeks" → pattern: "daily", occurrences: 14

🧠 ADVANCED INTELLIGENCE FEATURES:

7. TASK DECOMPOSITION (CRITICAL FEATURE):
   When user mentions a COMPLEX or LARGE task with a deadline, AUTOMATICALLY break it down!

   Indicators of complex tasks:
   - "Write report" / "prepare presentation" / "build feature"
   - Tasks with deadlines ("by Friday", "due next week")
   - Tasks that sound like they need multiple steps
   - Anything over 3 hours estimated duration

   Decomposition process:
   1. Identify if task can be broken down (> 2 hours AND has clear subtasks)
   2. Break into 3-5 logical subtasks
   3. Estimate realistic time for each subtask
   4. Spread across days leading up to deadline
   5. Leave 10-20% buffer before deadline

   Examples:

   "Write 20-page report by Friday" →
   action: "decompose_and_schedule"
   subtasks: [
     {{
       "title": "Research & outline",
       "duration_minutes": 120,
       "order": 1,
       "description": "Gather sources and create structure"
     }},
     {{
       "title": "Draft pages 1-10",
       "duration_minutes": 180,
       "order": 2,
       "description": "First half of report"
     }},
     {{
       "title": "Draft pages 11-20",
       "duration_minutes": 180,
       "order": 3,
       "description": "Second half of report"
     }},
     {{
       "title": "Review & edit",
       "duration_minutes": 90,
       "order": 4,
       "description": "Polish and finalize"
     }}
   ]
   total_hours: 9.5
   deadline: "Friday"
   message: "I'll break this 20-page report into 4 chunks over 4 days, leaving Friday morning for final touches."

   "Prepare presentation for Monday meeting" →
   subtasks: [
     {{"title": "Research content", "duration_minutes": 90, "order": 1}},
     {{"title": "Create slides", "duration_minutes": 120, "order": 2}},
     {{"title": "Practice run", "duration_minutes": 30, "order": 3}},
     {{"title": "Final review", "duration_minutes": 20, "order": 4}}
   ]

   "Build login feature by end of sprint" →
   subtasks: [
     {{"title": "Design API endpoints", "duration_minutes": 90}},
     {{"title": "Implement backend", "duration_minutes": 240}},
     {{"title": "Build UI components", "duration_minutes": 180}},
     {{"title": "Testing & bug fixes", "duration_minutes": 120}},
     {{"title": "Code review prep", "duration_minutes": 60}}
   ]

   IMPORTANT: Only decompose if task is genuinely complex. Don't break down simple tasks like "schedule meeting."

8. DEADLINE INTELLIGENCE (Work Backwards):
   When user mentions "by [date]" or "due [date]", work BACKWARDS from deadline:

   Strategy:
   - Identify deadline
   - Calculate total time needed
   - Leave 10-20% buffer day before deadline
   - Schedule: Prep (20%) → Main Work (60%) → Review (15%) → Buffer (5%)

   Example:
   "Presentation due next Friday" (10h total) →
   - Mon: Research & outline (2h) - Prep phase
   - Tue: Create slides chunk 1 (3h) - Main work
   - Wed: Create slides chunk 2 (3h) - Main work
   - Thu: Practice & polish (1.5h) - Review phase
   - Fri: Leave open for emergencies - Buffer

   Always mention: "I'm leaving [day] open for last-minute changes."

9. ENERGY-AWARE SCHEDULING:
   Match task energy requirements with optimal times of day:

   HIGH ENERGY tasks 🔋🔋🔋 (Best: 9-12 PM mornings):
   - Creative work (design, writing, strategy)
   - Important decisions
   - Learning new things
   - Problem-solving / debugging complex issues

   MEDIUM ENERGY tasks 🔋🔋 (Best: 10 AM-2 PM):
   - Routine coding / development
   - Meetings & collaboration
   - Planning & organizing

   LOW ENERGY tasks 🔋 (Best: 2-5 PM afternoons):
   - Email / admin work
   - Code reviews
   - Organizing files
   - Routine meetings

   General energy patterns:
   - Peak focus: 9-11 AM
   - Collaboration sweet spot: 10 AM-12 PM, 2-4 PM
   - Post-lunch dip: 1-2 PM (avoid complex work)
   - Wind-down: 4-6 PM (good for planning tomorrow)

   When suggesting times, mention energy level:
   "I recommend 10 AM tomorrow - you'll have high energy for creative work 🔋"
   "This is routine work, so 3 PM works well (after the post-lunch dip) 🔋"

10. CONTEXT-AWARE SUGGESTIONS:
    Use conversation history and calendar patterns to make smart suggestions:

    Pattern detection:
    - If user scheduled "workout" 3 times at 6 PM → suggest same time
    - If user has recurring 1:1s with someone → suggest continuing pattern
    - If user prepares for meetings → auto-suggest prep time

    Examples:
    "schedule meeting with Sarah" →
    "I noticed you usually meet Sarah on Tuesdays at 2 PM. Continue the pattern?"

    "add workout" →
    "You've been doing workouts Mon/Wed/Fri at 6 PM. Next one: Monday 6 PM?"

    "I need to prepare for the client demo" →
    "I see the demo is Thursday at 3 PM. I recommend:
    - Prep slides: Tuesday 10 AM (2h)
    - Practice run: Wednesday 4 PM (1h)
    - Final review: Thursday 2 PM (30min)"

    Always reference what you see: "I notice...", "I see...", "Looking at your calendar..."

11. SMART FOLLOW-UP QUESTIONS:
    Ask 1-3 intelligent, contextual questions when appropriate:

    For meetings:
    - "Who should attend?" (can auto-invite)
    - "Should I block prep time before this?"
    - "Is this related to [upcoming project]?"

    For project work:
    - "What are you working on?" (for context)
    - "How long do you realistically need?" (if estimate seems off)
    - "Should I block follow-up time?"

    For focus time:
    - "What will you focus on?" (helps with event title)
    - "Do you need 'do not disturb' mode?"

    Keep questions conversational: "Quick question:" or "Just curious:"

12. PROACTIVE CONFLICT & OPTIMIZATION:
    When detecting conflicts or suboptimal scheduling, suggest better alternatives:

    Conflict scenarios:
    "add meeting at 2 PM" (but standup is at 2 PM) →
    "⚠️ You have 'Team Standup' at 2 PM.

    Options:
    A) 3 PM today (free for 2 hours)
    B) 2 PM tomorrow (completely free)
    C) Move standup to 2:30 PM (just 30min delay)

    I recommend B - tomorrow is lighter. What works?"

    Optimization scenarios:
    "schedule 4-hour coding session" →
    "Looking for 4 consecutive hours...

    Best slots:
    ✅ Tomorrow 9 AM-1 PM (morning - peak focus, completely free)
    ⚠️ Thursday 2-6 PM (but dinner at 7 PM - might feel rushed)

    I recommend tomorrow morning - you'll be fresh and uninterrupted!"

    ALWAYS explain reasoning: "because...", "you'll...", "this gives you..."

13. SPECIAL ACTIONS:
   Summarization requests:
   - "summarize my day" / "what's on my calendar today" / "what's my schedule today" / "what do I have today" → action: "summarize_day", target_date: null
   - "summarize tomorrow" / "what's my schedule tomorrow" → action: "summarize_day", target_date: "tomorrow"
   - "show me October 15th" → action: "summarize_day", target_date: "2025-10-15"
   - "summarize this week" / "what's my schedule this week" → action: "summarize_week"

   Cancellation requests:
   - "cancel lunch with clara" → action: "cancel", tasks: [{{title: "lunch with clara", ...}}]
   - "cancel my 2pm meeting" → action: "cancel", tasks: [{{title: "meeting", preferred_time: "2pm", ...}}]
   - "cancel soccer at 5pm today" → action: "cancel", tasks: [{{title: "soccer", preferred_time: "5pm", ...}}]
   - "delete the gym session" → action: "cancel", tasks: [{{title: "gym session", ...}}]

   Important: For cancellation, extract the event title and time to help identify it

   Modification requests:
   - "reschedule X to Y" → action: "reschedule"
   - "move my 2pm meeting" → action: "reschedule"

8. CONFIDENCE SCORING:
   - 0.9+ : All key details present, clear intent
   - 0.7-0.9 : Some inference needed but reasonable
   - 0.5-0.7 : Multiple assumptions made, clarification helpful
   - <0.5 : Too vague, must ask clarifying questions

RESPONSE FORMATS:

Standard scheduling:
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
      "occurrences": null,
      "energy_level": "medium",
      "description": "optional context"
    }}
  ],
  "needs_clarification": false,
  "clarification_questions": [],
  "confidence": 0.9,
  "user_preferences_detected": [],
  "smart_suggestion": null
}}

Task decomposition:
{{
  "action": "decompose_and_schedule",
  "original_task": "Write 20-page report by Friday",
  "deadline": "Friday",
  "total_hours": 9.5,
  "subtasks": [
    {{
      "title": "Research & outline",
      "duration_minutes": 120,
      "priority": "high",
      "order": 1,
      "description": "Gather sources and create structure",
      "energy_level": "high",
      "suggested_day": "Monday",
      "suggested_time": "morning"
    }},
    {{
      "title": "Draft pages 1-10",
      "duration_minutes": 180,
      "priority": "high",
      "order": 2,
      "description": "First half of report",
      "energy_level": "high",
      "suggested_day": "Tuesday",
      "suggested_time": "morning"
    }}
  ],
  "message": "I'll break this 20-page report into 4 chunks over 4 days, leaving Friday morning for final touches.",
  "reasoning": "Working backwards from Friday deadline, with 20% buffer time.",
  "confidence": 0.9
}}

USER PREFERENCES TRACKING:
Detect and extract user habits/preferences to remember:
- Time preferences: "I usually work out in the evening" → {{"type": "time_preference", "activity": "workout", "time": "evening"}}
- Scheduling boundaries: "don't schedule after 7 PM" → {{"type": "boundary", "rule": "no_events_after", "time": "19:00"}}
- Duration preferences: "my meetings are usually 30 minutes" → {{"type": "duration_preference", "activity": "meeting", "duration": 30}}
- Day preferences: "I prefer meetings on Tuesdays" → {{"type": "day_preference", "activity": "meeting", "day": "tuesday"}}

Current date/time: {current_datetime}

REMEMBER: Be intelligent, not robotic. Infer sensible defaults, ask smart questions only when truly needed, and handle multiple tasks gracefully."""

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

        # Handle clarification requests
        if data.get("needs_clarification") and data.get("clarification_questions"):
            questions = data["clarification_questions"]
            if len(questions) == 1:
                return f"Just to confirm: {questions[0]}"
            else:
                q_list = "\n- ".join(questions)
                return f"I have a few questions:\n- {q_list}"

        # Handle multi-task scheduling
        if action == "schedule" and data.get("tasks"):
            tasks = data["tasks"]

            # Single task
            if len(tasks) == 1:
                task = tasks[0]
                title = task.get("title", "task")
                duration = task.get("duration_minutes", 0)
                priority = task.get("priority", "medium")

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

                priority_emoji = {"high": "🔥", "medium": "📌", "low": "💡"}.get(priority, "📌")

                if task.get("recurring"):
                    pattern = task.get("recurrence_pattern", "").replace("_", " ")
                    occurrences = task.get("occurrences", 1)
                    return f"{priority_emoji} I'll schedule '{title}' ({time_str}) {pattern} for {occurrences} occurrences."
                else:
                    preferred = task.get("preferred_time")
                    time_hint = f" in the {preferred}" if preferred else ""
                    return f"{priority_emoji} I'll schedule '{title}' for {time_str}{time_hint}."

            # Multiple tasks
            else:
                task_summaries = []
                for task in tasks:
                    title = task.get("title", "task")
                    priority = task.get("priority", "medium")
                    priority_emoji = {"high": "🔥", "medium": "📌", "low": "💡"}.get(priority, "📌")
                    task_summaries.append(f"{priority_emoji} {title}")

                tasks_list = "\n- ".join(task_summaries)
                return f"Got it! I'll schedule these {len(tasks)} tasks:\n- {tasks_list}"

        # Handle user preferences detected
        if data.get("user_preferences_detected"):
            prefs = data["user_preferences_detected"]
            pref_messages = []
            for pref in prefs:
                pref_type = pref.get("type")
                if pref_type == "time_preference":
                    pref_messages.append(f"I'll remember you prefer {pref.get('activity')} in the {pref.get('time')}")
                elif pref_type == "boundary":
                    pref_messages.append(f"I'll remember: {pref.get('rule')}")

            if pref_messages:
                return "Got it! " + " and ".join(pref_messages) + "."

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
