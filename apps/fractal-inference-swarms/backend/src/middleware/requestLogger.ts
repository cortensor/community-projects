import { Request, Response, NextFunction } from 'express';
import { createChildLogger } from '../utils/logger';

const logger = createChildLogger('HTTP');

export function requestLogger(req: Request, res: Response, next: NextFunction): void {
  const start = Date.now();

  res.on('finish', () => {
    const duration = Date.now() - start;
    const logData = {
      method: req.method,
      path: req.path,
      statusCode: res.statusCode,
      durationMs: duration,
      contentLength: res.get('content-length') || 0,
      userAgent: req.get('user-agent')?.slice(0, 80),
    };

    if (res.statusCode >= 400) {
      logger.warn('Request completed with error', logData);
    } else {
      logger.info('Request completed', logData);
    }
  });

  next();
}