import winston from 'winston';
import { config } from '../config';

const { combine, timestamp, printf, colorize, json } = winston.format;

const consoleFormat = printf(({ level, message, timestamp: ts, ...meta }) => {
  const metaStr = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : '';
  return `[${ts}] ${level}: ${message}${metaStr}`;
});

const transports: winston.transport[] = [
  new winston.transports.Console({
    format: config.logging.format === 'json'
      ? combine(timestamp(), json())
      : combine(colorize(), timestamp({ format: 'HH:mm:ss.SSS' }), consoleFormat),
  }),
];

if (config.server.nodeEnv === 'production') {
  transports.push(
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
      maxsize: 10 * 1024 * 1024,
      maxFiles: 5,
    }),
    new winston.transports.File({
      filename: 'logs/combined.log',
      maxsize: 10 * 1024 * 1024,
      maxFiles: 10,
    })
  );
}

export const logger = winston.createLogger({
  level: config.logging.level,
  defaultMeta: { service: 'fractal-inference-swarms' },
  transports,
});

export function createChildLogger(component: string): winston.Logger {
  return logger.child({ component });
}