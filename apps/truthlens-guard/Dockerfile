# TruthLens Backend Dockerfile for Render
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY backend/package*.json ./

# Install all dependencies (including dev dependencies for building)
RUN npm ci

# Copy backend source code
COPY backend/ ./

# Build the TypeScript code
RUN npm run build

# Install only production dependencies
RUN npm ci --only=production

# Create data directory for JSON storage
RUN mkdir -p src/data

# Expose port
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:10000/api/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1) }).on('error', () => process.exit(1))"

# Start the application
CMD ["npm", "start"]
