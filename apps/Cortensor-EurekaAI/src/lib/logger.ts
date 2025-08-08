// src/lib/logger.ts
type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LoggerConfig {
  level: LogLevel;
  enableInProduction: boolean;
}

class Logger {
  private config: LoggerConfig;
  
  constructor(config: LoggerConfig = { level: 'info', enableInProduction: false }) {
    this.config = config;
  }
  
  private shouldLog(level: LogLevel): boolean {
    if (!this.config.enableInProduction && process.env.NODE_ENV === 'production') {
      return level === 'error'; // Only show errors in production
    }
    return true;
  }
  
  private formatMessage(level: LogLevel, category: string, message: string, data?: any): void {
    if (!this.shouldLog(level)) return;
    
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] ${level.toUpperCase()} [${category}]`;
    
    switch (level) {
      case 'debug':
        console.debug(prefix, message, data || '');
        break;
      case 'info':
        console.info(prefix, message, data || '');
        break;
      case 'warn':
        console.warn(prefix, message, data || '');
        break;
      case 'error':
        console.error(prefix, message, data || '');
        break;
    }
  }
  
  debug(category: string, message: string, data?: any): void {
    this.formatMessage('debug', category, message, data);
  }
  
  info(category: string, message: string, data?: any): void {
    this.formatMessage('info', category, message, data);
  }
  
  warn(category: string, message: string, data?: any): void {
    this.formatMessage('warn', category, message, data);
  }
  
  error(category: string, message: string, data?: any): void {
    this.formatMessage('error', category, message, data);
  }
}

// Create singleton instance
export const logger = new Logger({
  level: process.env.NODE_ENV === 'production' ? 'error' : 'debug',
  enableInProduction: false
});

// Convenience exports for different categories
export const apiLogger = {
  debug: (message: string, data?: any) => logger.debug('API', message, data),
  info: (message: string, data?: any) => logger.info('API', message, data),
  warn: (message: string, data?: any) => logger.warn('API', message, data),
  error: (message: string, data?: any) => logger.error('API', message, data),
};

export const frontendLogger = {
  debug: (message: string, data?: any) => logger.debug('FRONTEND', message, data),
  info: (message: string, data?: any) => logger.info('FRONTEND', message, data),
  warn: (message: string, data?: any) => logger.warn('FRONTEND', message, data),
  error: (message: string, data?: any) => logger.error('FRONTEND', message, data),
};

export const storageLogger = {
  debug: (message: string, data?: any) => logger.debug('STORAGE', message, data),
  info: (message: string, data?: any) => logger.info('STORAGE', message, data),
  warn: (message: string, data?: any) => logger.warn('STORAGE', message, data),
  error: (message: string, data?: any) => logger.error('STORAGE', message, data),
};
