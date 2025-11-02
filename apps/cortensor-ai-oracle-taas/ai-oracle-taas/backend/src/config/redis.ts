import { createClient, type RedisClientType } from "redis"
import { logger } from "../utils/logger"

let redisClient: RedisClientType

export const connectRedis = async (): Promise<void> => {
  try {
    redisClient = createClient({
      url: process.env.REDIS_URL || "redis://:redis_password@localhost:6379",
      socket: {
        connectTimeout: 5000,
      },
    })

    redisClient.on("error", (err) => {
      logger.error("Redis Client Error:", err)
    })

    redisClient.on("connect", () => {
      logger.info("Redis client connected")
    })

    redisClient.on("ready", () => {
      logger.info("Redis client ready")
    })

    await redisClient.connect()

    // Test connection
    await redisClient.ping()
    logger.info("Redis connection established")
  } catch (error) {
    logger.error("Redis connection failed:", error)
    throw error
  }
}

export const getRedis = (): RedisClientType => {
  if (!redisClient) {
    throw new Error("Redis not initialized. Call connectRedis() first.")
  }
  return redisClient
}

export const closeRedis = async (): Promise<void> => {
  if (redisClient) {
    await redisClient.quit()
    logger.info("Redis connection closed")
  }
}
