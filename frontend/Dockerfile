# Frontend Dockerfile - Multi-stage build
# Stage 1: Dependencies
FROM node:18-alpine AS deps

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Stage 2: Builder
FROM node:18-alpine AS builder

WORKDIR /app

# Copy everything
COPY . .

# Install dependencies again (simpler approach)
RUN npm install

# Build the application
RUN npm run build

# Stage 3: Runner
FROM node:18-alpine AS runner

WORKDIR /app

# Set environment to production
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Copy package files
COPY --from=builder /app/package*.json ./

# Install production dependencies only
RUN npm ci --omit=dev

# Copy built application
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./

# Expose port
EXPOSE 3000

# Set PORT environment variable (Railway compatibility)
ENV PORT=3000

# Start the application
CMD ["npm", "start"]
