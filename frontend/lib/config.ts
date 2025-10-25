/**
 * Application Configuration
 * Environment variables for the CalBot frontend
 */

export const config = {
  // API Base URL - must be set in Railway environment variables
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',

  // Google OAuth Client ID
  googleClientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
} as const;

// Log configuration on client side (for debugging)
if (typeof window !== 'undefined') {
  console.log('CalBot Config:', {
    apiUrl: config.apiUrl,
    hasGoogleClientId: !!config.googleClientId,
  });
}

export default config;
