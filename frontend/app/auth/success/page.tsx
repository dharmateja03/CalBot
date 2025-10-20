"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";

export default function AuthSuccessPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setToken } = useAuth();
  const processedRef = useRef(false);

  useEffect(() => {
    // Prevent double processing in React Strict Mode
    if (processedRef.current) return;

    const token = searchParams.get("token");

    if (token) {
      processedRef.current = true;

      // Store token and update auth state
      setToken(token);

      // Redirect to main app after a brief delay
      setTimeout(() => {
        router.push("/");
      }, 1500);
    } else {
      // No token provided, redirect to error
      router.push("/auth/error?message=No token provided");
    }
  }, [searchParams, setToken, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="mb-4">
          <svg
            className="w-16 h-16 text-green-500 mx-auto animate-bounce"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <h1 className="text-2xl font-semibold text-gray-900 mb-2">
          Authentication Successful!
        </h1>
        <p className="text-gray-600">Redirecting to CalBot...</p>
      </div>
    </div>
  );
}
