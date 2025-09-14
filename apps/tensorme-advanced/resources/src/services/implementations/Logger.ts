import { injectable } from 'inversify';
import { ILogger, LogLevel, LogContext } from '../interfaces';

@injectable()
export class Logger implements ILogger {
  private level: LogLevel;

  constructor() {
    this.level = process.env.NODE_ENV === 'production' 
      ? LogLevel.INFO 
      : LogLevel.DEBUG;
  }

  debug(message: string, context?: LogContext): void {
    if (this.level <= LogLevel.DEBUG) {
      console.debug(this.format('DEBUG', message, context));
    }
  }

  info(message: string, context?: LogContext): void {
    if (this.level <= LogLevel.INFO) {
      console.info(this.format('INFO', message, context));
    }
  }

  warn(message: string, context?: LogContext): void {
    if (this.level <= LogLevel.WARN) {
      console.warn(this.format('WARN', message, context));
    }
  }

  error(message: string, error?: Error, context?: LogContext): void {
    if (this.level <= LogLevel.ERROR) {
      const formatted = this.format('ERROR', message, context);
      console.error(formatted, error);
      
      // Send to monitoring in production
      if (process.env.NODE_ENV === 'production') {
        this.sendToMonitoring(message, error, context);
      }
    }
  }

  private format(level: string, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString();
    const contextStr = context ? JSON.stringify(context) : '';
    return `[${timestamp}] [${level}] ${message} ${contextStr}`;
  }

  private sendToMonitoring(message: string, error?: Error, context?: LogContext): void {
    // Integration with monitoring service (Sentry, DataDog, etc.)
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      (window as any).Sentry.captureException(error || new Error(message), {
        extra: context,
      });
    }
  }
}