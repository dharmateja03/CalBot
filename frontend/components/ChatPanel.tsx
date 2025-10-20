"use client";

import { useState, useRef, useEffect } from "react";
import { CalendarEvent } from "@/types/calendar";
import { useAuth } from "@/contexts/AuthContext";
import { sendChatMessage, getUserTimezone } from "@/lib/api";

interface Message {
  id: string;
  type: "user" | "bot";
  content: string;
  timestamp: Date;
}

interface ChatPanelProps {
  selectedEvent: CalendarEvent | null;
  onClose: () => void;
  onAddEvents: (events: CalendarEvent[]) => void;
}

export default function ChatPanel({ selectedEvent: _selectedEvent, onClose, onAddEvents }: ChatPanelProps) {
  const { user, isAuthenticated } = useAuth();
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasShownWelcomeRef = useRef(false);

  // Helper function to get username from email
  const getUsernameFromEmail = (email: string): string => {
    // Extract name before @ symbol and capitalize first letter
    const username = email.split('@')[0];
    return username.charAt(0).toUpperCase() + username.slice(1);
  };

  // Initial messages (will be updated when user logs in)
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      type: "bot",
      content:
        "Hi! I'm CalBot. Tell me what you'd like to schedule and I'll find the perfect time for it. Try saying something like 'Schedule 2 hours for marketing report tomorrow'",
      timestamp: new Date(),
    },
  ]);

  // Show personalized welcome message when user logs in
  useEffect(() => {
    if (isAuthenticated && user && !hasShownWelcomeRef.current) {
      hasShownWelcomeRef.current = true;

      const username = getUsernameFromEmail(user.email);
      const timezone = getUserTimezone();

      const welcomeMessage: Message = {
        id: "welcome-" + Date.now(),
        type: "bot",
        content: `Hi ${username}! 👋\n\nI'm CalBot, your AI scheduling assistant. I've detected your timezone as ${timezone}.\n\nIf you'd like to change your timezone or other preferences, you can do so in Settings.\n\nWhat would you like to schedule today?`,
        timestamp: new Date(),
      };

      setMessages([welcomeMessage]);
    }
  }, [isAuthenticated, user]);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    // Check if user is authenticated
    if (!isAuthenticated) {
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: "bot",
        content: "Please sign in with Google to use CalBot and sync with your calendar.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const messageText = input;
    setInput("");
    setIsLoading(true);

    try {
      // Call backend API using the API client
      const data = await sendChatMessage(messageText, user?.id);

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "bot",
        content: data.reply || "I processed your request!",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);

      // If there are scheduled tasks, add them to the calendar
      if (data.scheduled_tasks && data.scheduled_tasks.length > 0) {
        console.log("Received scheduled tasks:", data.scheduled_tasks);
        const newEvents: CalendarEvent[] = data.scheduled_tasks.map((task: any) => ({
          id: task.calendar_event_id,
          title: task.title,
          start: new Date(task.start),
          end: new Date(task.end),
          description: task.description,
          priority: "medium", // Default priority, can be enhanced later
        }));
        console.log("Adding events to calendar:", newEvents);
        onAddEvents(newEvents);
        console.log("Events added successfully");
      }

      // If there are clarification questions, add them
      if (data.needs_clarification && data.clarification_questions?.length > 0) {
        const questionsMessage: Message = {
          id: (Date.now() + 2).toString(),
          type: "bot",
          content: data.clarification_questions.join("\n"),
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, questionsMessage]);
      }

      // If there's a conflict, show conflict details
      if (data.has_conflict && data.conflicts && data.conflicts.length > 0) {
        const conflict = data.conflicts[0];
        const conflictTime = new Date(conflict.start);
        const conflictMessage: Message = {
          id: (Date.now() + 3).toString(),
          type: "bot",
          content: `⚠️ You already have "${conflict.title}" scheduled at ${conflictTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.\n\nWould you like to schedule both events at the same time? Reply with 'yes' to confirm or 'no' to cancel.`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, conflictMessage]);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "bot",
        content: "Sorry, I encountered an error. Please make sure the backend server is running.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickActions = [
    "Schedule 2 hours for report tomorrow",
    "Gym every day for next 10 days",
    "Cancel tomorrow's meeting",
  ];

  return (
    <div className="h-full flex flex-col" style={{ backgroundColor: 'var(--background)' }}>
      {/* Chat Header - Dark Theme */}
      <div className="p-4 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--accent-cyan), var(--event-deepwork))' }}>
            <svg className="w-5 h-5" fill="white" viewBox="0 0 20 20">
              <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
              <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
            </svg>
          </div>
          <div>
            <h2 className="text-sm font-medium" style={{ color: 'var(--foreground)' }}>AI Assistant</h2>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>CalBot</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded transition-colors"
          style={{ color: 'var(--text-muted)' }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.type === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className="max-w-[80%] rounded-lg px-4 py-2"
              style={{
                backgroundColor: message.type === "user"
                  ? 'var(--accent-cyan)'
                  : 'var(--surface)',
                color: message.type === "user"
                  ? 'var(--background)'
                  : 'var(--foreground)',
                border: message.type === "bot" ? '1px solid var(--border)' : 'none'
              }}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              <p
                className="text-xs mt-1"
                style={{
                  color: message.type === "user"
                    ? 'rgba(14, 14, 17, 0.7)'
                    : 'var(--text-muted)'
                }}
              >
                {message.timestamp.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="rounded-lg px-4 py-2" style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}>
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: 'var(--accent-cyan)' }} />
                <div className="w-2 h-2 rounded-full animate-bounce delay-100" style={{ backgroundColor: 'var(--accent-cyan)' }} />
                <div className="w-2 h-2 rounded-full animate-bounce delay-200" style={{ backgroundColor: 'var(--accent-cyan)' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      {messages.length <= 2 && (
        <div className="px-4 py-2" style={{ borderTop: '1px solid var(--border)' }}>
          <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>Quick actions:</p>
          <div className="space-y-2">
            {quickActions.map((action, index) => (
              <button
                key={index}
                onClick={() => setInput(action)}
                className="w-full text-left px-3 py-2 text-sm rounded-lg transition-colors"
                style={{
                  color: 'var(--foreground)',
                  backgroundColor: 'var(--surface)',
                  border: '1px solid var(--border)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(46, 233, 226, 0.1)';
                  e.currentTarget.style.borderColor = 'var(--accent-cyan)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--surface)';
                  e.currentTarget.style.borderColor = 'var(--border)';
                }}
              >
                {action}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="p-4" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your task here..."
            rows={2}
            className="flex-1 px-4 py-2 rounded-lg resize-none focus:outline-none transition-all"
            style={{
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
              color: 'var(--foreground)'
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'var(--accent-cyan)';
              e.currentTarget.style.boxShadow = '0 0 0 2px rgba(46, 233, 226, 0.1)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'var(--border)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 rounded-lg transition-all self-end"
            style={{
              background: !input.trim() || isLoading
                ? 'var(--text-dimmed)'
                : 'linear-gradient(135deg, var(--accent-cyan), var(--event-deepwork))',
              color: 'white',
              cursor: !input.trim() || isLoading ? 'not-allowed' : 'pointer'
            }}
            onMouseEnter={(e) => {
              if (input.trim() && !isLoading) {
                e.currentTarget.style.transform = 'translateY(-1px)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
