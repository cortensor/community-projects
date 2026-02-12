import { Request, Response, NextFunction } from 'express';
import { createChildLogger } from '../utils/logger';

const logger = createChildLogger('ErrorHandler');

export interface ApiError extends Error {
  statusCode?: number;
  details?: unknown;
}

export function errorHandler(err: ApiError, _req: Request, res: Response, _next: NextFunction): void {
  const statusCode = err.statusCode || 500;
  const message = err.message || 'Internal server error';

  logger.error('Unhandled error', {
    statusCode,
    message,
    stack: err.stack,
    details: err.details,
  });

  res.status(statusCode).json({
    error: message,
    statusCode,
    details: process.env.NODE_ENV === 'development' ? err.details || err.stack : undefined,
    timestamp: Date.now(),
  });
}

export function notFoundHandler(_req: Request, res: Response): void {
  res.status(404).json({
    error: 'Endpoint not found',
    statusCode: 404,
    timestamp: Date.now(),
  });
}