/**
 * API Client for CalBot Backend
 * Handles all HTTP requests to FastAPI backend
 */

import { getAuthToken } from "./auth";
import { config } from './config';

const API_BASE_URL = config.apiUrl;

/**
 * Get user's timezone using browser API
 */
export function getUserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch (error) {
    console.warn("Failed to detect timezone, defaulting to UTC:", error);
    return "UTC";
  }
}

/**
 * Get auth headers for API requests
 */
function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    "X-Timezone": getUserTimezone(), // Auto-detect user's timezone
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

export interface ChatMessage {
  message: string;
  user_id?: string;
}

export interface ScheduledTask {
  title: string;
  start: string;
  end: string;
  calendar_event_id: string;
  description?: string;
}

export interface ChatResponse {
  reply: string;
  scheduled_tasks: ScheduledTask[];
  needs_clarification: boolean;
  clarification_questions: string[];
  success: boolean;
}

export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  description?: string;
}

/**
 * Send a chat message and get AI response with scheduling
 */
export async function sendChatMessage(message: string, userId?: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      message,
      user_id: userId || "demo_user",
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to send message");
  }

  return response.json();
}

/**
 * Get calendar events within a date range
 */
export async function getCalendarEvents(
  startDate?: string,
  endDate?: string
): Promise<{ events: CalendarEvent[] }> {
  const params = new URLSearchParams();
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);

  const response = await fetch(`${API_BASE_URL}/calendar/events?${params}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error("Failed to fetch calendar events");
  }

  return response.json();
}

/**
 * Sync calendar with Google Calendar
 */
export async function syncCalendar(): Promise<{
  synced: boolean;
  events_imported: number;
  last_sync: string;
}> {
  const response = await fetch(`${API_BASE_URL}/calendar/sync`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error("Failed to sync calendar");
  }

  return response.json();
}

/**
 * Get user preferences
 */
export async function getPreferences(): Promise<{
  work_hours: { start: string; end: string };
  break_time: { start: string; end: string };
  timezone: string;
  preferred_deep_work_time?: string;
  preferred_meeting_time?: string;
}> {
  const response = await fetch(`${API_BASE_URL}/preferences`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error("Failed to fetch preferences");
  }

  return response.json();
}

/**
 * Update user preferences
 */
export async function updatePreferences(preferences: {
  work_hours?: { start: string; end: string };
  break_time?: { start: string; end: string };
  timezone?: string;
  preferred_deep_work_time?: string;
  preferred_meeting_time?: string;
}): Promise<{ message: string; preferences: any }> {
  const response = await fetch(`${API_BASE_URL}/preferences`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(preferences),
  });

  if (!response.ok) {
    throw new Error("Failed to update preferences");
  }

  return response.json();
}

/**
 * Delete a task
 */
export async function deleteTask(taskId: string): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  return response.ok;
}

/**
 * Get chat history
 */
export async function getChatHistory(): Promise<{
  messages: Array<{ id: string; message: string; response: string; created_at: string }>;
  count: number;
}> {
  const response = await fetch(`${API_BASE_URL}/chat/history`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error("Failed to fetch chat history");
  }

  return response.json();
}
