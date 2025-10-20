"use client";

import React, { createContext, useContext, useState, useEffect, useRef } from "react";
import {
  User,
  AuthState,
  getCurrentUser,
  initiateGoogleLogin,
  logout as logoutUser,
  getAuthToken,
  setAuthToken,
  clearAuthToken,
} from "@/lib/auth";

interface AuthContextType extends AuthState {
  login: () => void;
  logout: () => Promise<void>;
  setToken: (token: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
  });

  const initializedRef = useRef(false);

  // Initialize auth state on mount
  useEffect(() => {
    // Prevent double initialization in React Strict Mode
    if (initializedRef.current) return;
    initializedRef.current = true;

    const initAuth = async () => {
      const token = getAuthToken();

      if (token) {
        // Verify token and get user
        const user = await getCurrentUser(token);

        if (user) {
          setState({
            user,
            token,
            isAuthenticated: true,
            isLoading: false,
          });
        } else {
          // Token invalid, clear it
          clearAuthToken();
          setState({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      } else {
        setState({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        });
      }
    };

    initAuth();
  }, []);

  const login = () => {
    initiateGoogleLogin();
  };

  const logout = async () => {
    if (state.token) {
      await logoutUser(state.token);
    }

    clearAuthToken();
    setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    });
  };

  const setToken = async (token: string) => {
    // Only set if it's a new token
    if (state.token === token) return;

    setAuthToken(token);

    // Fetch user data
    const user = await getCurrentUser(token);

    if (user) {
      setState({
        user,
        token,
        isAuthenticated: true,
        isLoading: false,
      });
    } else {
      // Token invalid
      clearAuthToken();
      setState({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  };

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        logout,
        setToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
