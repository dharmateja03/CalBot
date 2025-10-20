"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

interface HeaderProps {
  onToggleChat: () => void;
  isChatOpen: boolean;
}

export default function Header({ onToggleChat, isChatOpen }: HeaderProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { user, isAuthenticated, login, logout: handleLogout } = useAuth();

  // Get user initials for avatar
  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .substring(0, 2);
  };

  const userAvatar = user ? getInitials(user.name) : "?";

  return (
    <>
      <header className="h-16 border-b px-6 flex items-center justify-between" style={{ backgroundColor: 'var(--background)', borderColor: 'var(--border)' }}>
        {/* Left: Logo */}
        <div className="flex items-center gap-3">
          <svg className="w-10 h-10" viewBox="0 0 24 24" fill="none">
            <rect x="3" y="4" width="18" height="18" rx="3" fill="url(#gradient)" />
            <defs>
              <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#2EE9E2" />
                <stop offset="100%" stopColor="#2CB5B1" />
              </linearGradient>
            </defs>
            <text x="12" y="17" fontSize="13" fill="white" textAnchor="middle" fontWeight="bold">CB</text>
          </svg>
          <span className="text-xl font-semibold" style={{ color: 'var(--foreground)' }}>CalBot</span>
        </div>

        {/* Right: Chat Toggle & Profile */}
        <div className="flex items-center gap-4">
          {/* Chat Toggle Button */}
          <button
            onClick={onToggleChat}
            className={`p-2 rounded-full transition-all ${isChatOpen ? 'glow-active' : ''}`}
            title="AI Assistant"
            style={{
              backgroundColor: isChatOpen ? 'rgba(46, 233, 226, 0.15)' : 'transparent',
              border: isChatOpen ? '1px solid var(--accent-cyan)' : 'none'
            }}
            onMouseEnter={(e) => !isChatOpen && (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)')}
            onMouseLeave={(e) => !isChatOpen && (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ color: isChatOpen ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </button>

          {/* User Profile */}
          <div className="relative">
            {isAuthenticated && user ? (
              <>
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="w-10 h-10 rounded-full flex items-center justify-center font-medium text-sm transition-all"
                  style={{
                    background: 'linear-gradient(135deg, var(--accent-cyan), var(--event-deepwork))',
                    color: 'white'
                  }}
                >
                  {userAvatar}
                </button>

                {/* Dropdown Menu */}
                {isDropdownOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setIsDropdownOpen(false)}
                    />

                    <div className="absolute right-0 mt-2 w-72 rounded-lg shadow-2xl py-2 z-20" style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}>
                      <div className="px-4 py-3 text-center" style={{ borderBottom: '1px solid var(--border)' }}>
                        <div className="w-16 h-16 rounded-full flex items-center justify-center font-medium text-2xl mx-auto mb-2" style={{ background: 'linear-gradient(135deg, var(--accent-cyan), var(--event-deepwork))' }}>
                          <span style={{ color: 'white' }}>{userAvatar}</span>
                        </div>
                        <div className="font-medium" style={{ color: 'var(--foreground)' }}>{user.name}</div>
                        <div className="text-sm" style={{ color: 'var(--text-muted)' }}>{user.email}</div>
                      </div>

                      <button
                        onClick={() => {
                          setIsDropdownOpen(false);
                          handleLogout();
                        }}
                        className="w-full text-left px-4 py-2 text-sm transition-colors"
                        style={{ color: 'var(--text-muted)', borderTop: '1px solid var(--border)' }}
                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'}
                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                      >
                        Sign out
                      </button>
                    </div>
                  </>
                )}
              </>
            ) : (
              <button
                onClick={login}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                style={{
                  background: 'linear-gradient(135deg, var(--accent-cyan), var(--event-deepwork))',
                  color: 'white'
                }}
                onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-1px)'}
                onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
              >
                Sign in with Google
              </button>
            )}
          </div>
        </div>
      </header>
    </>
  );
}
