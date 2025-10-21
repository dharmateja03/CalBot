"""
Database Service
Handles all Supabase database interactions
"""

import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for backend

# Create client if credentials available
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("✅ Supabase client initialized")
else:
    supabase = None
    print("⚠️  Supabase credentials not found. Database features disabled.")


class DatabaseService:
    """Service for database operations"""

    @staticmethod
    def create_or_update_user(google_id: str, email: str, name: str, picture: Optional[str] = None) -> Dict:
        """
        Create or update user in database

        Args:
            google_id: Google OAuth user ID
            email: User email
            name: User's full name
            picture: Profile picture URL

        Returns:
            User data dict
        """
        if not supabase:
            # Return mock data if DB not available
            return {
                "id": google_id,
                "google_id": google_id,
                "email": email,
                "name": name,
                "picture": picture
            }

        try:
            # Check if user exists
            existing = supabase.table("users").select("*").eq("google_id", google_id).execute()

            if existing.data:
                # Update existing user
                result = supabase.table("users").update({
                    "email": email,
                    "name": name,
                    "picture": picture,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("google_id", google_id).execute()

                print(f"✅ Updated user: {email}")
                return result.data[0]
            else:
                # Create new user
                result = supabase.table("users").insert({
                    "google_id": google_id,
                    "email": email,
                    "name": name,
                    "picture": picture
                }).execute()

                # Create default preferences for new user
                DatabaseService.create_default_preferences(result.data[0]['id'])

                print(f"✅ Created new user: {email}")
                return result.data[0]

        except Exception as e:
            print(f"❌ Database error creating/updating user: {e}")
            return None

    @staticmethod
    def get_user_by_google_id(google_id: str) -> Optional[Dict]:
        """Get user by Google ID"""
        if not supabase:
            return None

        try:
            result = supabase.table("users").select("*").eq("google_id", google_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error fetching user: {e}")
            return None

    @staticmethod
    def store_oauth_tokens(
        user_id: str,
        access_token: str,
        refresh_token: Optional[str],
        client_id: str,
        client_secret: str,
        scopes: List[str],
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Store or update OAuth tokens for a user

        Args:
            user_id: User UUID
            access_token: Google OAuth access token
            refresh_token: Google OAuth refresh token
            client_id: OAuth client ID
            client_secret: OAuth client secret
            scopes: List of OAuth scopes
            expires_at: Token expiration time

        Returns:
            True if successful
        """
        if not supabase:
            return False

        try:
            # Check if tokens exist
            existing = supabase.table("oauth_tokens").select("*").eq("user_id", user_id).execute()

            token_data = {
                "user_id": user_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": scopes,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "updated_at": datetime.utcnow().isoformat()
            }

            if existing.data:
                # Update existing tokens
                supabase.table("oauth_tokens").update(token_data).eq("user_id", user_id).execute()
                print(f"✅ Updated OAuth tokens for user: {user_id}")
            else:
                # Insert new tokens
                supabase.table("oauth_tokens").insert(token_data).execute()
                print(f"✅ Stored OAuth tokens for user: {user_id}")

            return True

        except Exception as e:
            print(f"❌ Error storing OAuth tokens: {e}")
            return False

    @staticmethod
    def get_oauth_tokens(user_id: str) -> Optional[Dict]:
        """Get OAuth tokens for a user"""
        if not supabase:
            return None

        try:
            result = supabase.table("oauth_tokens").select("*").eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error fetching OAuth tokens: {e}")
            return None

    @staticmethod
    def create_default_preferences(user_id: str) -> bool:
        """Create default preferences for a new user"""
        if not supabase:
            return False

        try:
            supabase.table("user_preferences").insert({
                "user_id": user_id,
                "work_hours_start": "09:00:00",
                "work_hours_end": "17:00:00",
                "break_start": "12:00:00",
                "break_end": "13:00:00",
                "timezone": "UTC",
                "preferred_meeting_duration": 60
            }).execute()

            print(f"✅ Created default preferences for user: {user_id}")
            return True

        except Exception as e:
            print(f"❌ Error creating default preferences: {e}")
            return False

    @staticmethod
    def get_user_preferences(user_id: str) -> Optional[Dict]:
        """Get user preferences"""
        if not supabase:
            # Return default preferences if DB not available
            return {
                "work_hours_start": "09:00:00",
                "work_hours_end": "17:00:00",
                "break_start": "12:00:00",
                "break_end": "13:00:00",
                "timezone": "UTC",
                "preferred_meeting_duration": 60
            }

        try:
            result = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error fetching preferences: {e}")
            return None

    @staticmethod
    def update_user_preferences(user_id: str, preferences: Dict) -> bool:
        """Update user preferences"""
        if not supabase:
            return False

        try:
            supabase.table("user_preferences").update({
                **preferences,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("user_id", user_id).execute()

            print(f"✅ Updated preferences for user: {user_id}")
            return True

        except Exception as e:
            print(f"❌ Error updating preferences: {e}")
            return False

    @staticmethod
    def add_conversation_message(user_id: str, role: str, content: str) -> bool:
        """
        Add a message to conversation history

        Args:
            user_id: User UUID
            role: 'user' or 'assistant'
            content: Message content

        Returns:
            True if successful
        """
        if not supabase:
            return False

        try:
            supabase.table("conversations").insert({
                "user_id": user_id,
                "role": role,
                "content": content
            }).execute()

            return True

        except Exception as e:
            print(f"❌ Error adding conversation message: {e}")
            return False

    @staticmethod
    def get_conversation_history(user_id: str, limit: int = 20) -> List[Dict]:
        """
        Get recent conversation history for a user

        Args:
            user_id: User UUID
            limit: Number of recent messages to retrieve

        Returns:
            List of conversation messages
        """
        if not supabase:
            return []

        try:
            result = supabase.table("conversations")\
                .select("role, content, created_at")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()

            # Reverse to get chronological order
            messages = list(reversed(result.data)) if result.data else []

            return messages

        except Exception as e:
            print(f"❌ Error fetching conversation history: {e}")
            return []

    @staticmethod
    def clear_conversation_history(user_id: str) -> bool:
        """Clear all conversation history for a user"""
        if not supabase:
            return False

        try:
            supabase.table("conversations").delete().eq("user_id", user_id).execute()
            supabase.table("conversation_summaries").delete().eq("user_id", user_id).execute()

            print(f"✅ Cleared conversation history for user: {user_id}")
            return True

        except Exception as e:
            print(f"❌ Error clearing conversation history: {e}")
            return False

    @staticmethod
    def store_conversation_summary(user_id: str, summary: str, message_count: int) -> bool:
        """Store or update conversation summary"""
        if not supabase:
            return False

        try:
            # Check if summary exists
            existing = supabase.table("conversation_summaries").select("*").eq("user_id", user_id).execute()

            summary_data = {
                "user_id": user_id,
                "summary": summary,
                "message_count": message_count
            }

            if existing.data:
                # Update existing summary
                supabase.table("conversation_summaries").update(summary_data).eq("user_id", user_id).execute()
            else:
                # Insert new summary
                supabase.table("conversation_summaries").insert(summary_data).execute()

            print(f"✅ Stored conversation summary for user: {user_id}")
            return True

        except Exception as e:
            print(f"❌ Error storing conversation summary: {e}")
            return False

    @staticmethod
    def get_conversation_summary(user_id: str) -> Optional[str]:
        """Get conversation summary for a user"""
        if not supabase:
            return None

        try:
            result = supabase.table("conversation_summaries").select("summary").eq("user_id", user_id).execute()
            return result.data[0]['summary'] if result.data else None
        except Exception as e:
            print(f"❌ Error fetching conversation summary: {e}")
            return None

    @staticmethod
    def create_session(user_id: str, token: str, expires_at: datetime) -> bool:
        """Create a new session"""
        if not supabase:
            return False

        try:
            supabase.table("sessions").insert({
                "user_id": user_id,
                "token": token,
                "expires_at": expires_at.isoformat()
            }).execute()

            print(f"✅ Created session for user: {user_id}")
            return True

        except Exception as e:
            print(f"❌ Error creating session: {e}")
            return False

    @staticmethod
    def get_session(token: str) -> Optional[Dict]:
        """Get session by token"""
        if not supabase:
            return None

        try:
            result = supabase.table("sessions")\
                .select("*")\
                .eq("token", token)\
                .gt("expires_at", datetime.utcnow().isoformat())\
                .execute()

            return result.data[0] if result.data else None

        except Exception as e:
            print(f"❌ Error fetching session: {e}")
            return None

    @staticmethod
    def delete_session(token: str) -> bool:
        """Delete a session (logout)"""
        if not supabase:
            return False

        try:
            supabase.table("sessions").delete().eq("token", token).execute()
            print(f"✅ Deleted session")
            return True

        except Exception as e:
            print(f"❌ Error deleting session: {e}")
            return False

    @staticmethod
    def clean_expired_sessions() -> bool:
        """Clean up expired sessions"""
        if not supabase:
            return False

        try:
            supabase.rpc("clean_expired_sessions").execute()
            print("✅ Cleaned up expired sessions")
            return True

        except Exception as e:
            print(f"❌ Error cleaning expired sessions: {e}")
            return False

