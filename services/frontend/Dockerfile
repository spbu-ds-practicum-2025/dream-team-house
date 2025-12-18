FROM node:20-alpine AS builder

WORKDIR /app

# --- Build-time public env for Next.js (embedded into client bundles) ---
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_CHAT_URL
ARG NEXT_PUBLIC_ANALYTICS_URL

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_CHAT_URL=${NEXT_PUBLIC_CHAT_URL}
ENV NEXT_PUBLIC_ANALYTICS_URL=${NEXT_PUBLIC_ANALYTICS_URL}

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build


# ---- Production runtime image (Next.js standalone) ----
FROM node:20-alpine AS runner

WORKDIR /app
ENV NODE_ENV=production

# (Optional) for debugging inside container:
# RUN apk add --no-cache curl

# Copy standalone server + required node_modules subset
# This produces /app/server.js and /app/node_modules (minimal) inside standalone output
COPY --from=builder /app/.next/standalone ./

# Copy static assets (Next requires this path at runtime)
COPY --from=builder /app/.next/static ./.next/static

# Copy public assets if you have them
#COPY --from=builder /app/public ./public

# Run as non-root user
USER node

EXPOSE 3000

# Start Next.js standalone server
CMD ["node", "server.js"]