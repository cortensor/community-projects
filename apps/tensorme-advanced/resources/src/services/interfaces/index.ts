// Common types
export type Unsubscribe = () => void;

// Task Service
export interface TaskRequest {
  type: 'chat' | 'research';
  payload: any;
  sessionId?: string;
}

export interface TaskResponse {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

export interface TaskStatus {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

export interface ITaskService {
  submitTask(task: TaskRequest): Promise<TaskResponse>;
  getTaskStatus(taskId: string): Promise<TaskStatus>;
  cancelTask(taskId: string): Promise<void>;
  onTaskComplete(callback: (task: TaskStatus) => void): Unsubscribe;
}

// Stream Service
export interface StreamParams {
  endpoint: string;
  headers?: Record<string, string>;
  body?: any;
}

export interface StreamHandle {
  id: string;
  close(): void;
  onChunk(callback: (chunk: string) => void): Unsubscribe;
  onEnd(callback: () => void): Unsubscribe;
  onError(callback: (error: Error) => void): Unsubscribe;
}

export interface StreamState {
  id: string;
  isActive: boolean;
  buffer: string;
  chunks: string[];
  startTime: number;
  endTime?: number;
}

export interface IStreamService {
  createStream(params: StreamParams): StreamHandle;
  processChunk(streamId: string, chunk: string): void;
  endStream(streamId: string): void;
  getStreamState(streamId: string): StreamState | null;
  cleanup(streamId: string): void;
}

// Research Service
export interface ResearchOptions {
  mode: 'fast' | 'standard' | 'deep';
  maxAgents: number;
  timeout: number;
  domains: string[];
  includeCode: boolean;
  maxDepth: number;
}

export interface ResearchSession {
  id: string;
  query: string;
  options: ResearchOptions;
  status: 'pending' | 'active' | 'completed' | 'failed';
  startTime: number;
}

export interface ResearchUpdate {
  type: 'progress' | 'finding' | 'error' | 'complete';
  data: any;
}

export interface IResearchService {
  startResearch(query: string, options: ResearchOptions): Promise<ResearchSession>;
  getResearchStatus(sessionId: string): Promise<ResearchSession>;
  streamResults(sessionId: string): AsyncGenerator<ResearchUpdate>;
  stopResearch(sessionId: string): Promise<void>;
}

// HTTP Client
export interface HttpResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
  headers: Record<string, string>;
}

export interface IHttpClient {
  get<T = any>(url: string, config?: RequestInit): Promise<HttpResponse<T>>;
  post<T = any>(url: string, data?: any, config?: RequestInit): Promise<HttpResponse<T>>;
  put<T = any>(url: string, data?: any, config?: RequestInit): Promise<HttpResponse<T>>;
  del<T = any>(url: string, config?: RequestInit): Promise<HttpResponse<T>>;
}

// Logger
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

export interface LogContext {
  userId?: string;
  sessionId?: string;
  requestId?: string;
  [key: string]: unknown;
}

export interface ILogger {
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string, error?: Error, context?: LogContext): void;
}

// Event Bus
export interface IEventBus {
  emit(event: string, data?: any): void;
  on(event: string, callback: (data?: any) => void): Unsubscribe;
  off(event: string, callback: (data?: any) => void): void;
  once(event: string, callback: (data?: any) => void): Unsubscribe;
}