# Svelte Frontend Dockerfile - Multi-stage build
# Stage 1: Build the Svelte application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY ui/package.json ui/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY ui/ ./

# Build the application
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy built files from builder
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
