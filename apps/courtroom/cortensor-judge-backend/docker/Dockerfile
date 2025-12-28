# Node.js Builder
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY sentinel/package.json sentinel/package-lock.json ./
COPY judge-sdk/package.json ./judge-sdk/

# Install dependencies
RUN npm ci

# Copy source code
COPY sentinel/src ./src
COPY sentinel/tsconfig.json ./

# Build
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Copy package files
COPY sentinel/package.json sentinel/package-lock.json ./

# Install production dependencies only
RUN npm ci --only=production

# Copy built application
COPY --from=builder /app/dist ./dist

# Create non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
USER nodejs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3001/health', (res) => { if (res.statusCode === 200) process.exit(0); else process.exit(1); })" || exit 1

# Use dumb-init to handle signals properly
ENTRYPOINT ["/sbin/dumb-init", "--"]

# Start application
CMD ["node", "dist/index.js"]

EXPOSE 3001
