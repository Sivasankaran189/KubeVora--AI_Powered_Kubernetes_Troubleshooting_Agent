# ==============================================================================
# Multi-Stage Production Dockerfile for KubeVora React Frontend
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build static assets
# ------------------------------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

# Accept build argument for backend API URL
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Install node dependencies
COPY package*.json ./
RUN npm ci --prefer-offline --no-audit

# Copy source files and compile Vite SPA bundle
COPY . .
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Nginx Server
# ------------------------------------------------------------------------------
FROM nginx:alpine

# Clean default configuration
RUN rm -rf /etc/nginx/conf.d/*

# Copy custom Nginx configuration with SPA fallback
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled SPA bundle from builder stage
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 3000

# Health check to ensure Nginx is responding on port 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
