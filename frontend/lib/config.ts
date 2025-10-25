/**
 * Application Configuration
 * Environment variables for the CalBot frontend
 */

export const config = {
  // API Base URL - use environment variable or Railway backend
  apiUrl: process.env.NEXT_PUBLIC_API_URL ||
          (typeof window !== 'undefined' && window.location.hostname !== 'localhost'
            ? 'https://calbot-production-6ce3.up.railway.app'
            : 'http://localhost:8000'),

  // Google OAuth Client ID
  googleClientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '792060021027-edpprr7ebjqbnnc3doft32oopa0fbldl.apps.googleusercontent.com',
} as const;

// Log configuration on client side (for debugging)
if (typeof window !== 'undefined') {
  console.log('CalBot Config:', {
    apiUrl: config.apiUrl,
    hasGoogleClientId: !!config.googleClientId,
  });
}

export default config;
