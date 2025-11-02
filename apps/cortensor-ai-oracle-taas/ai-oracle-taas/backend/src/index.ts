import express from "express"
import cors from "cors"
import helmet from "helmet"
import morgan from "morgan"
import compression from "compression"
import rateLimit from "express-rate-limit"
import { createServer } from "http"
import { WebSocketServer } from "ws"
import dotenv from "dotenv"

import { logger } from "./utils/logger"
import { connectDatabase } from "./config/database"
import { connectRedis } from "./config/redis"
import { setupWebSocket } from "./services/websocketService"

// Routes
import oracleRoutes from "./routes/oracle"
import queryRoutes from "./routes/queries"
import adminRoutes from "./routes/admin"
import authRoutes from "./routes/auth"

// Load environment variables
dotenv.config()

const app = express()
const server = createServer(app)
const wss = new WebSocketServer({ server })

// Middleware
app.use(helmet())
app.use(
  cors({
    origin: process.env.FRONTEND_URL || "http://localhost:3000",
    credentials: true,
  }),
)
app.use(compression())
app.use(morgan("combined", { stream: { write: (message) => logger.info(message.trim()) } }))
app.use(express.json({ limit: "10mb" }))
app.use(express.urlencoded({ extended: true }))

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: "Too many requests from this IP, please try again later.",
})
app.use(limiter)

// Health check
app.get("/health", (req, res) => {
  res.status(200).json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  })
})

// API Routes
app.use("/api/auth", authRoutes)
app.use("/api/oracle", oracleRoutes)
app.use("/api/queries", queryRoutes)
app.use("/api/admin", adminRoutes)

// Error handling middleware
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  logger.error("Unhandled error:", err)
  res.status(500).json({
    error: "Internal server error",
    message: process.env.NODE_ENV === "development" ? err.message : "Something went wrong",
  })
})

// 404 handler
app.use("*", (req, res) => {
  res.status(404).json({ error: "Route not found" })
})

// Initialize services
async function startServer() {
  try {
    // Connect to database
    await connectDatabase()
    logger.info("Database connected successfully")

    // Connect to Redis
    await connectRedis()
    logger.info("Redis connected successfully")

    // Setup WebSocket
    setupWebSocket(wss)
    logger.info("WebSocket server initialized")

    const PORT = process.env.PORT || 4000
    server.listen(PORT, () => {
      logger.info(`AI Oracle Backend running on port ${PORT}`)
      logger.info(`Environment: ${process.env.NODE_ENV}`)
    })
  } catch (error) {
    logger.error("Failed to start server:", error)
    process.exit(1)
  }
}

// Graceful shutdown
process.on("SIGTERM", () => {
  logger.info("SIGTERM received, shutting down gracefully")
  server.close(() => {
    logger.info("Process terminated")
    process.exit(0)
  })
})

process.on("SIGINT", () => {
  logger.info("SIGINT received, shutting down gracefully")
  server.close(() => {
    logger.info("Process terminated")
    process.exit(0)
  })
})

startServer()
