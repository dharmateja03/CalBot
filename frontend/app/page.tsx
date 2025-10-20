"use client";

import { useState, useEffect } from "react";
import CalendarView from "@/components/CalendarView";
import ChatPanel from "@/components/ChatPanel";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import { CalendarEvent } from "@/types/calendar";
import { getCalendarEvents } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function Home() {
  const { isAuthenticated } = useAuth();
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);

  // Fetch events from Google Calendar
  const fetchEvents = async () => {
    if (!isAuthenticated) {
      console.log("Not authenticated, skipping event fetch");
      return;
    }

    try {
      setIsLoadingEvents(true);

      // Get events for the next 30 days
      const startDate = new Date();
      startDate.setHours(0, 0, 0, 0);
      const endDate = new Date();
      endDate.setDate(endDate.getDate() + 30);

      console.log("Fetching events from", startDate, "to", endDate);

      const response = await getCalendarEvents(
        startDate.toISOString(),
        endDate.toISOString()
      );

      console.log("Received events:", response.events);

      // Convert API response to CalendarEvent format
      const calendarEvents: CalendarEvent[] = response.events.map((event: any) => ({
        id: event.id,
        title: event.title,
        start: new Date(event.start),
        end: new Date(event.end),
        description: event.description,
        priority: 'medium', // Default priority
      }));

      console.log("Converted to calendar events:", calendarEvents);
      setEvents(calendarEvents);
    } catch (error) {
      console.error("Failed to fetch calendar events:", error);
      // Keep existing events on error
    } finally {
      setIsLoadingEvents(false);
    }
  };

  // Fetch events when user logs in
  useEffect(() => {
    if (isAuthenticated) {
      console.log("User authenticated, fetching events...");
      fetchEvents();
    }
  }, [isAuthenticated]);

  // Callback to add new events from ChatPanel
  const handleAddEvents = (newEvents: CalendarEvent[]) => {
    console.log("handleAddEvents called with:", newEvents);
    setEvents((prev) => {
      const updated = [...prev, ...newEvents];
      console.log("Updated events array:", updated);
      return updated;
    });

    // Refresh from server after a short delay
    setTimeout(() => {
      console.log("Refreshing events from server...");
      fetchEvents();
    }, 1500);
  };

  return (
    <div className="h-screen flex flex-col" style={{ backgroundColor: 'var(--background)' }}>
      {/* Header */}
      <Header onToggleChat={() => setIsChatOpen(!isChatOpen)} isChatOpen={isChatOpen} />

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Main Calendar Area */}
        <div className="flex-1 overflow-auto">
          <CalendarView events={events} onEventClick={setSelectedEvent} />
        </div>

        {/* Right Chat Panel */}
        {isChatOpen && (
          <div className="w-80 flex-shrink-0" style={{ borderLeft: '1px solid var(--border)' }}>
            <ChatPanel
              selectedEvent={selectedEvent}
              onClose={() => setIsChatOpen(false)}
              onAddEvents={handleAddEvents}
            />
          </div>
        )}
      </div>
    </div>
  );
}
