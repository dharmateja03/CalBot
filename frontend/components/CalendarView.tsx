"use client";

import { useState, useEffect } from "react";
import { CalendarEvent } from "@/types/calendar";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { format, startOfWeek, addDays, isSameDay, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth } from "date-fns";

interface CalendarViewProps {
  events: CalendarEvent[];
  onEventClick: (event: CalendarEvent | null) => void;
}

export default function CalendarView({ events, onEventClick }: CalendarViewProps) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [activeView, setActiveView] = useState<'day' | 'week'>('week');
  const [selectedDay, setSelectedDay] = useState(new Date());
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update current time every minute
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 60000); // Update every minute

    return () => clearInterval(timer);
  }, []);

  // Navigation handlers
  const handlePrev = () => {
    const newDate = new Date(activeView === 'day' ? selectedDay : currentDate);
    const daysToSubtract = activeView === 'day' ? 1 : 7;
    newDate.setDate(newDate.getDate() - daysToSubtract);

    if (activeView === 'day') {
      setSelectedDay(newDate);
      setCurrentDate(newDate);
    } else {
      setCurrentDate(newDate);
    }
  };

  const handleNext = () => {
    const newDate = new Date(activeView === 'day' ? selectedDay : currentDate);
    const daysToAdd = activeView === 'day' ? 1 : 7;
    newDate.setDate(newDate.getDate() + daysToAdd);

    if (activeView === 'day') {
      setSelectedDay(newDate);
      setCurrentDate(newDate);
    } else {
      setCurrentDate(newDate);
    }
  };

  const handlePrevMonth = () => {
    const newDate = new Date(currentDate);
    newDate.setMonth(currentDate.getMonth() - 1);
    setCurrentDate(newDate);
  };

  const handleNextMonth = () => {
    const newDate = new Date(currentDate);
    newDate.setMonth(currentDate.getMonth() + 1);
    setCurrentDate(newDate);
  };

  // Get week dates
  const getWeekDates = () => {
    const start = startOfWeek(currentDate);
    return Array.from({ length: 7 }, (_, i) => addDays(start, i));
  };

  // Get month calendar dates
  const getMonthDates = () => {
    const start = startOfMonth(currentDate);
    const end = endOfMonth(currentDate);
    return eachDayOfInterval({ start, end });
  };

  const weekDates = getWeekDates();
  const monthDates = getMonthDates();
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const hours = Array.from({ length: 24 }, (_, i) => i); // Full day: 0-23 hours

  // Week number and range calculation
  const getWeekNumber = (date: Date) => {
    const firstDayOfYear = new Date(date.getFullYear(), 0, 1);
    const pastDaysOfYear = (date.getTime() - firstDayOfYear.getTime()) / 86400000;
    return Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);
  };

  const weekNumber = getWeekNumber(currentDate);
  const weekStart = weekDates[0];
  const weekEnd = weekDates[6];

  // Get events for a specific date
  const getEventsForDate = (date: Date) => {
    return events.filter((event) => isSameDay(event.start, date));
  };

  // Calculate event position and height
  const calculateEventStyle = (event: CalendarEvent) => {
    const startHour = event.start.getHours() + event.start.getMinutes() / 60;
    const endHour = event.end.getHours() + event.end.getMinutes() / 60;
    const hourHeight = 60; // 60px per hour (Google Calendar style)
    const top = startHour * hourHeight;
    const height = (endHour - startHour) * hourHeight;
    return { top: `${top}px`, height: `${height}px` };
  };

  // Get event color based on title
  const getEventColor = (title: string) => {
    const titleLower = title.toLowerCase();
    if (titleLower.includes('course') || titleLower.includes('class')) return '#D65D8C';
    if (titleLower.includes('meditation') || titleLower.includes('zen')) return '#3CB76D';
    if (titleLower.includes('reading') || titleLower.includes('research')) return '#D98A34';
    if (titleLower.includes('report') || titleLower.includes('writing')) return '#A2D239';
    if (titleLower.includes('running') || titleLower.includes('gym')) return '#D7C548';
    if (titleLower.includes('deep work') || titleLower.includes('focus')) return '#2CB5B1';
    return '#2CB5B1'; // default
  };

  // Calculate current time indicator position
  const getCurrentTimePosition = () => {
    const hours = currentTime.getHours();
    const minutes = currentTime.getMinutes();
    const hourHeight = 60; // 60px per hour
    const top = (hours + minutes / 60) * hourHeight;
    return top;
  };

  // Check if date is today
  const isToday = (date: Date) => {
    const today = new Date();
    return isSameDay(date, today);
  };

  // Calculate duration
  const getDuration = (event: CalendarEvent) => {
    const durationMs = event.end.getTime() - event.start.getTime();
    const hours = Math.floor(durationMs / (1000 * 60 * 60));
    const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
    if (hours === 0) return `${minutes}m`;
    if (minutes === 0) return `${hours}h`;
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="flex h-full">
      {/* Left Sidebar - Mini Month Calendar */}
      <div className="w-64 p-4 flex-shrink-0" style={{ borderRight: '1px solid var(--border)' }}>
        {/* Month Navigation */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={handlePrevMonth}
            className="p-1 rounded transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--foreground)'}
            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            <ChevronLeft size={16} />
          </button>
          <h3 className="text-sm font-medium" style={{ color: 'var(--foreground)' }}>
            {format(currentDate, 'MMMM yyyy')}
          </h3>
          <button
            onClick={handleNextMonth}
            className="p-1 rounded transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--foreground)'}
            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Mini Calendar Grid - Traditional Calendar Layout */}
        <div>
          {/* Day headers (S M T W T F S) */}
          <div className="grid grid-cols-7 gap-1 mb-2">
            {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, index) => (
              <div
                key={index}
                className="text-xs font-medium text-center py-1"
                style={{ color: 'var(--text-muted)' }}
              >
                {day}
              </div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7 gap-1">
            {/* Add empty cells for days before month starts */}
            {Array.from({ length: startOfMonth(currentDate).getDay() }).map((_, index) => (
              <div key={`empty-${index}`} className="w-8 h-8" />
            ))}

            {/* Month dates */}
            {monthDates.map((date) => {
              const isSelected = isSameDay(date, selectedDay);
              const isToday = isSameDay(date, new Date());
              const dayNumber = format(date, 'd');

              return (
                <button
                  key={date.toString()}
                  onClick={() => {
                    setSelectedDay(date);
                    setCurrentDate(date);
                  }}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all"
                  style={{
                    backgroundColor: isToday
                      ? 'var(--accent-cyan)'
                      : isSelected
                      ? 'rgba(46, 233, 226, 0.2)'
                      : 'transparent',
                    color: isToday
                      ? 'var(--background)'
                      : isSelected
                      ? 'var(--accent-cyan)'
                      : 'var(--text-muted)',
                    fontWeight: isToday || isSelected ? '600' : '400'
                  }}
                  onMouseEnter={(e) => {
                    if (!isToday && !isSelected) {
                      e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isToday && !isSelected) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  {dayNumber}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Calendar Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="w-full max-w-5xl mx-auto px-4 py-8 flex flex-col h-full">
          {/* Top Navigation */}
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center">
              <h1 className="text-base font-medium" style={{ color: 'var(--foreground)' }}>
                {format(currentDate, 'MMMM yyyy')}
              </h1>
              <div className="ml-4 flex gap-2">
                <button
                  onClick={handlePrev}
                  className="transition-colors p-1"
                  style={{ color: 'var(--text-muted)' }}
                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--foreground)'}
                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                  title={activeView === 'day' ? 'Previous day' : 'Previous week'}
                >
                  <ChevronLeft size={18} />
                </button>
                <button
                  onClick={handleNext}
                  className="transition-colors p-1"
                  style={{ color: 'var(--text-muted)' }}
                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--foreground)'}
                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                  title={activeView === 'day' ? 'Next day' : 'Next week'}
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            </div>

            <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
              W{weekNumber}, {format(weekStart, 'MMM d')} - {format(weekEnd, 'MMM d')}
            </div>

            <div className="flex items-center gap-4">
              {/* View Switcher */}
              <div className="flex rounded-full p-0.5" style={{ backgroundColor: '#1E1E21' }}>
                <button
                  onClick={() => setActiveView('day')}
                  className="px-3 py-1 rounded-full text-sm transition-colors"
                  style={{
                    backgroundColor: activeView === 'day' ? '#2C2C2F' : 'transparent',
                    color: activeView === 'day' ? 'var(--foreground)' : 'var(--text-muted)'
                  }}
                >
                  Day
                </button>
                <button
                  onClick={() => setActiveView('week')}
                  className="px-3 py-1 rounded-full text-sm transition-colors"
                  style={{
                    backgroundColor: activeView === 'week' ? '#2C2C2F' : 'transparent',
                    color: activeView === 'week' ? 'var(--foreground)' : 'var(--text-muted)'
                  }}
                >
                  Week
                </button>
              </div>

              {/* Add Button */}
              <button
                className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
                style={{ border: '1px solid var(--border)', color: 'var(--foreground)' }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent-cyan)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
              >
                <Plus size={16} />
              </button>
            </div>
          </div>

          {/* Day Selector - Show week view day selector or single day header */}
          {activeView === 'week' ? (
            <div className="flex justify-between mt-4 gap-2">
              {weekDates.map((date, index) => {
                const isSelected = isSameDay(date, selectedDay);
                const isToday = isSameDay(date, new Date());

                return (
                  <button
                    key={index}
                    onClick={() => setSelectedDay(date)}
                    className="flex flex-col items-center justify-center w-12 h-12 rounded-full transition-all"
                    style={{
                      backgroundColor: isSelected
                        ? 'var(--accent-cyan)'
                        : isToday
                        ? 'var(--accent-red)'
                        : 'var(--text-dimmed)',
                      color: isSelected || isToday ? 'white' : 'var(--text-muted)',
                      boxShadow: isSelected ? '0 0 15px rgba(46, 233, 226, 0.5)' : 'none'
                    }}
                  >
                    <span className="text-xs">{days[index]}</span>
                    <span className="text-sm font-medium">{date.getDate()}</span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="mt-4 p-4 rounded-xl text-center" style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}>
              <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {format(selectedDay, 'EEEE')}
              </div>
              <div className="text-2xl font-bold mt-1" style={{ color: 'var(--foreground)' }}>
                {format(selectedDay, 'MMMM d, yyyy')}
              </div>
              <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                {isSameDay(selectedDay, new Date()) ? 'Today' : format(selectedDay, 'EEEE')}
              </div>
            </div>
          )}

          {/* Calendar Grid */}
          <div className="flex-1 overflow-y-auto mt-6">
            <div className="relative">
              {/* Time indicators */}
              <div className="absolute left-0 top-0 w-16 h-full flex flex-col">
                {hours.map((hour) => (
                  <div key={hour} className="h-[60px] flex items-start justify-start relative">
                    <span className="text-xs absolute -top-2" style={{ color: 'var(--text-muted)' }}>
                      {hour === 0 ? '12 AM' : hour === 12 ? '12 PM' : hour < 12 ? `${hour} AM` : `${hour - 12} PM`}
                    </span>
                  </div>
                ))}
              </div>

              {/* Grid - Conditional rendering based on activeView */}
              <div className={`ml-16 grid ${activeView === 'day' ? 'grid-cols-1' : 'grid-cols-7'} gap-2`}>
                {(activeView === 'day' ? [selectedDay] : weekDates).map((date, dateIndex) => (
                  <div key={dateIndex} className="relative">
                    {/* Hour lines */}
                    {hours.map((hour) => (
                      <div
                        key={hour}
                        className="h-[60px]"
                        style={{
                          borderTop: '1px solid var(--border)',
                          opacity: 0.3
                        }}
                      />
                    ))}

                    {/* Events */}
                    {getEventsForDate(date).map((event, eventIndex) => {
                      const style = calculateEventStyle(event);
                      const color = getEventColor(event.title);

                      return (
                        <div
                          key={eventIndex}
                          className="absolute w-[98%] left-0 cursor-pointer"
                          style={style}
                          onClick={() => onEventClick(event)}
                        >
                          <div
                            className="rounded-xl p-3 w-full h-full text-white overflow-hidden transition-all hover:brightness-110"
                            style={{
                              backgroundColor: color,
                              opacity: 0.95
                            }}
                          >
                            <h3 className="text-base font-medium leading-tight">{event.title}</h3>
                            <p className="text-[13px] mt-0.5" style={{ color: '#DADADA' }}>
                              {getDuration(event)}
                            </p>
                          </div>
                        </div>
                      );
                    })}

                    {/* Current time indicator (red line) */}
                    {isToday(date) && (
                      <div
                        className="absolute left-0 right-0 z-50 pointer-events-none"
                        style={{
                          top: `${getCurrentTimePosition()}px`,
                        }}
                      >
                        {/* Red circle indicator */}
                        <div
                          className="absolute -left-1.5 -top-1.5 w-3 h-3 rounded-full"
                          style={{
                            backgroundColor: '#EA4335',
                          }}
                        />
                        {/* Red line */}
                        <div
                          className="w-full h-0.5"
                          style={{
                            backgroundColor: '#EA4335',
                          }}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
