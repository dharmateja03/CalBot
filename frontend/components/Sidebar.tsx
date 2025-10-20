"use client";

import { useState } from "react";

export default function Sidebar() {
  const [currentDate, setCurrentDate] = useState(new Date());

  // Generate calendar days
  const getDaysInMonth = (date: Date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startDayOfWeek = firstDay.getDay();

    const days = [];

    // Add empty cells for days before month starts
    for (let i = 0; i < startDayOfWeek; i++) {
      days.push(null);
    }

    // Add days of month
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }

    return days;
  };

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  const days = getDaysInMonth(currentDate);
  const today = new Date();

  const prevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1));
  };

  return (
    <div className="w-64 border-r border-gray-200 bg-white flex flex-col">
      {/* Create Button */}
      <div className="p-4">
        <button className="flex items-center gap-3 px-4 py-3 rounded-full shadow hover:shadow-md transition-shadow bg-white border border-gray-300">
          <svg className="w-8 h-8" viewBox="0 0 36 36">
            <path fill="#4285F4" d="M16 16v14h4V20z"></path>
            <path fill="#EA4335" d="M30 16H20l-4 4h14z"></path>
            <path fill="#FBBC04" d="M6 16v4h10l4-4z"></path>
            <path fill="#34A853" d="M20 16V6h-4v14z"></path>
            <path fill="none" d="M0 0h36v36H0z"></path>
          </svg>
          <span className="font-medium text-gray-700">Create</span>
        </button>
      </div>

      {/* Mini Calendar */}
      <div className="px-4 pb-4">
        {/* Month Navigation */}
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-medium text-gray-700">
            {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
          </div>
          <div className="flex gap-1">
            <button
              onClick={prevMonth}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              onClick={nextMonth}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Day Headers */}
        <div className="grid grid-cols-7 gap-1 mb-1">
          {["S", "M", "T", "W", "T", "F", "S"].map((day, i) => (
            <div key={i} className="text-xs text-center text-gray-600 font-medium">
              {day}
            </div>
          ))}
        </div>

        {/* Calendar Grid */}
        <div className="grid grid-cols-7 gap-1">
          {days.map((day, index) => {
            const isToday =
              day === today.getDate() &&
              currentDate.getMonth() === today.getMonth() &&
              currentDate.getFullYear() === today.getFullYear();

            return (
              <div key={index} className="aspect-square">
                {day ? (
                  <button
                    className={`w-full h-full text-xs rounded-full flex items-center justify-center hover:bg-gray-100 ${
                      isToday
                        ? "bg-blue-600 text-white hover:bg-blue-700"
                        : "text-gray-700"
                    }`}
                  >
                    {day}
                  </button>
                ) : (
                  <div />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* My Calendars */}
      <div className="px-4 py-2">
        <div className="text-xs font-medium text-gray-600 mb-2">My calendars</div>

        <label className="flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-2 cursor-pointer">
          <input type="checkbox" defaultChecked className="rounded" />
          <div className="flex items-center gap-2 flex-1">
            <div className="w-3 h-3 bg-blue-600 rounded-sm"></div>
            <span className="text-sm text-gray-700">CalBot Tasks</span>
          </div>
        </label>

        <label className="flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-2 cursor-pointer">
          <input type="checkbox" defaultChecked className="rounded" />
          <div className="flex items-center gap-2 flex-1">
            <div className="w-3 h-3 bg-green-600 rounded-sm"></div>
            <span className="text-sm text-gray-700">Personal</span>
          </div>
        </label>

        <label className="flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-2 cursor-pointer">
          <input type="checkbox" defaultChecked className="rounded" />
          <div className="flex items-center gap-2 flex-1">
            <div className="w-3 h-3 bg-purple-600 rounded-sm"></div>
            <span className="text-sm text-gray-700">Work</span>
          </div>
        </label>
      </div>
    </div>
  );
}
