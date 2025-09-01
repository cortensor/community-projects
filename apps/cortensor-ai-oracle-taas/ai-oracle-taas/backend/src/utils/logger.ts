import winston from 'winston'
import path from 'path'
import fs from 'fs'

// Ensure logs directory exists
const logsDir = path.join(process.cwd(), 'logs')
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir, { recursive: true })
}

// Simple format for all logs
const logFormat = winston.format.combine(
  winston.format.timestamp({
    format: 'YYYY-MM-DD HH:mm:ss'
  }),
  winston.format.errors({ stack: true }),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    let output = `[${timestamp}] ${level.toUpperCase()}: ${message}`
    
    // Add metadata if present
    if (Object.keys(meta).length > 0) {
      output += ` ${JSON.stringify(meta)}`
    }
    
    return output
  })
)

// Create the logger instance
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: logFormat,
  transports: [
    // Write all logs to combined.log
    new winston.transports.File({ 
      filename: path.join(logsDir, 'combined.log'),
      maxsize: 10485760, // 10MB
      maxFiles: 5
    }),
    
    // Write errors to error.log
    new winston.transports.File({ 
      filename: path.join(logsDir, 'error.log'),
      level: 'error',
      maxsize: 10485760, // 10MB
      maxFiles: 5
    }),
    
    // Console output for development
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.timestamp({
          format: 'HH:mm:ss'
        }),
        winston.format.printf(({ timestamp, level, message, ...meta }) => {
          let output = `[${timestamp}] ${level.toUpperCase()}: ${message}`
          
          if (Object.keys(meta).length > 0) {
            output += ` ${JSON.stringify(meta)}`
          }
          
          return output
        })
      )
    })
  ]
})

// If we're not in production, also log to console with more verbose output
if (process.env.NODE_ENV !== 'production') {
  logger.level = 'debug'
}

// Helper methods for specific logging scenarios
const loggerUtils = {
  // Log consensus building process
  consensus: (message: string, data?: any) => {
    logger.info(message, { service: 'consensus', ...data })
  },

  // Log miner-related activities
  miner: (message: string, minerId?: string, data?: any) => {
    logger.info(message, { service: 'miner', minerId, ...data })
  },

  // Log algorithm execution
  algorithm: (algorithmName: string, message: string, data?: any) => {
    logger.debug(message, { service: 'algorithm', algorithm: algorithmName, ...data })
  },

  // Log performance metrics
  performance: (operation: string, duration: number, data?: any) => {
    logger.info(`${operation} completed`, { duration: `${duration}ms`, ...data })
  },

  // Log API requests
  api: (method: string, endpoint: string, status: number, duration?: number) => {
    logger.info(`${method} ${endpoint} ${status}`, { 
      service: 'api', 
      method, 
      endpoint, 
      status,
      ...(duration && { duration: `${duration}ms` })
    })
  },

  // Log database operations
  db: (operation: string, table?: string, duration?: number) => {
    logger.debug(`DB ${operation}`, { 
      service: 'database', 
      operation, 
      ...(table && { table }),
      ...(duration && { duration: `${duration}ms` })
    })
  },

  // Log network operations
  network: (operation: string, target: string, data?: any) => {
    logger.debug(`Network ${operation}`, { service: 'network', target, ...data })
  }
}

// Extend the logger with utility methods
const extendedLogger = Object.assign(logger, loggerUtils)

export { extendedLogger as logger }
export type Logger = typeof extendedLogger