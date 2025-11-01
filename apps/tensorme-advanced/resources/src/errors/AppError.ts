export abstract class AppError extends Error {
  public readonly id: string;
  public readonly timestamp: Date;
  public readonly isOperational: boolean;

  constructor(
    public readonly code: string,
    message: string,
    public readonly statusCode: number = 500,
    public readonly details?: unknown,
    isOperational: boolean = true,
  ) {
    super(message);
    this.id = crypto.randomUUID();
    this.timestamp = new Date();
    this.isOperational = isOperational;
    
    Object.setPrototypeOf(this, new.target.prototype);
    Error.captureStackTrace(this, this.constructor);
  }

  toJSON() {
    return {
      id: this.id,
      code: this.code,
      message: this.message,
      statusCode: this.statusCode,
      details: this.details,
      timestamp: this.timestamp,
    };
  }
}

export class ValidationError extends AppError {
  constructor(message: string, details?: unknown) {
    super('VALIDATION_ERROR', message, 400, details);
  }
}

export class AuthenticationError extends AppError {
  constructor(message: string = 'Authentication required') {
    super('AUTHENTICATION_ERROR', message, 401);
  }
}

export class NetworkError extends AppError {
  constructor(message: string, details?: unknown) {
    super('NETWORK_ERROR', message, 503, details);
  }
}

export class StreamError extends AppError {
  constructor(message: string, public readonly streamId: string) {
    super('STREAM_ERROR', message, 500, { streamId });
  }
}

export class TaskError extends AppError {
  constructor(message: string, public readonly taskId: string) {
    super('TASK_ERROR', message, 500, { taskId });
  }
}

export class ConfigurationError extends AppError {
  constructor(message: string, details?: unknown) {
    super('CONFIGURATION_ERROR', message, 500, details);
  }
}