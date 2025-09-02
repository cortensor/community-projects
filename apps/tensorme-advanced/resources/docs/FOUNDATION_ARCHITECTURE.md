# Foundation Architecture Implementation Guide

## Overview
This document demonstrates the foundational architecture patterns that should be implemented first. These examples show the structure without modifying your existing code.

## 1. State Management Foundation (Redux Toolkit)

### Store Configuration

```typescript
// store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import chatReducer from './slices/chatSlice';
import userReducer from './slices/userSlice';
import configReducer from './slices/configSlice';
import { apiSlice } from './api/apiSlice';

export const store = configureStore({
  reducer: {
    chat: chatReducer,
    user: userReducer,
    config: configReducer,
    [apiSlice.reducerPath]: apiSlice.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ['chat/streamUpdate', 'chat/addMessage'],
        // Ignore these field paths in all actions
        ignoredActionPaths: ['payload.timestamp', 'payload.file'],
        // Ignore these paths in the state
        ignoredPaths: ['chat.activeStreams'],
      },
    }).concat(apiSlice.middleware),
});

setupListeners(store.dispatch);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

### Core State Slices

```typescript
// store/slices/chatSlice.ts
import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { Message, ChatSession } from '@/types';

interface ChatState {
  sessions: Record<string, ChatSession>;
  currentSessionId: string | null;
  activeStreams: Record<string, StreamState>;
  ui: {
    isSidebarOpen: boolean;
    isResearchMode: boolean;
    selectedResponseIndex: Record<string, number>;
  };
  error: {
    message: string;
    code: string;
    sessionId?: string;
  } | null;
}

interface StreamState {
  buffer: string;
  isStreaming: boolean;
  startTime: number;
  chunks: string[];
}

const initialState: ChatState = {
  sessions: {},
  currentSessionId: null,
  activeStreams: {},
  ui: {
    isSidebarOpen: false,
    isResearchMode: false,
    selectedResponseIndex: {},
  },
  error: null,
};

// Async thunks for complex operations
export const loadChatSessions = createAsyncThunk(
  'chat/loadSessions',
  async (userId: string) => {
    // Load from localStorage or API
    const stored = localStorage.getItem(`chat_sessions_${userId}`);
    if (stored) {
      return JSON.parse(stored);
    }
    return {};
  }
);

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (
    params: {
      sessionId: string;
      message: string;
      modelId: string;
      domainId?: string;
    },
    { dispatch, getState }
  ) => {
    // Start streaming
    dispatch(startStream({ sessionId: params.sessionId }));
    
    // Call API
    const response = await fetch('/api/chat/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    // Return stream reader
    return response.body?.getReader();
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    // Synchronous actions
    createSession: (state, action: PayloadAction<{ id: string; name: string }>) => {
      state.sessions[action.payload.id] = {
        id: action.payload.id,
        name: action.payload.name,
        messages: [],
        timestamp: Date.now(),
        isLoading: false,
      };
      state.currentSessionId = action.payload.id;
    },

    selectSession: (state, action: PayloadAction<string>) => {
      if (state.sessions[action.payload]) {
        state.currentSessionId = action.payload;
      }
    },

    addMessage: (state, action: PayloadAction<{ sessionId: string; message: Message }>) => {
      const session = state.sessions[action.payload.sessionId];
      if (session) {
        session.messages.push(action.payload.message);
        session.timestamp = Date.now();
      }
    },

    startStream: (state, action: PayloadAction<{ sessionId: string }>) => {
      state.activeStreams[action.payload.sessionId] = {
        buffer: '',
        isStreaming: true,
        startTime: Date.now(),
        chunks: [],
      };
    },

    appendStreamChunk: (state, action: PayloadAction<{ sessionId: string; chunk: string }>) => {
      const stream = state.activeStreams[action.payload.sessionId];
      if (stream) {
        stream.buffer += action.payload.chunk;
        stream.chunks.push(action.payload.chunk);
      }
    },

    endStream: (state, action: PayloadAction<{ sessionId: string }>) => {
      const stream = state.activeStreams[action.payload.sessionId];
      if (stream) {
        stream.isStreaming = false;
        // Convert buffer to message
        const session = state.sessions[action.payload.sessionId];
        if (session && stream.buffer) {
          const lastMessage = session.messages[session.messages.length - 1];
          if (lastMessage && lastMessage.role === 'assistant') {
            lastMessage.content = stream.buffer;
          }
        }
        // Clean up stream
        delete state.activeStreams[action.payload.sessionId];
      }
    },

    toggleSidebar: (state) => {
      state.ui.isSidebarOpen = !state.ui.isSidebarOpen;
    },

    toggleResearchMode: (state) => {
      state.ui.isResearchMode = !state.ui.isResearchMode;
    },

    setError: (state, action: PayloadAction<ChatState['error']>) => {
      state.error = action.payload;
    },

    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadChatSessions.fulfilled, (state, action) => {
        state.sessions = action.payload;
      })
      .addCase(sendMessage.pending, (state, action) => {
        const sessionId = action.meta.arg.sessionId;
        if (state.sessions[sessionId]) {
          state.sessions[sessionId].isLoading = true;
        }
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        const sessionId = action.meta.arg.sessionId;
        if (state.sessions[sessionId]) {
          state.sessions[sessionId].isLoading = false;
        }
      })
      .addCase(sendMessage.rejected, (state, action) => {
        const sessionId = action.meta.arg.sessionId;
        if (state.sessions[sessionId]) {
          state.sessions[sessionId].isLoading = false;
        }
        state.error = {
          message: action.error.message || 'Failed to send message',
          code: 'SEND_MESSAGE_ERROR',
          sessionId,
        };
      });
  },
});

export const {
  createSession,
  selectSession,
  addMessage,
  startStream,
  appendStreamChunk,
  endStream,
  toggleSidebar,
  toggleResearchMode,
  setError,
  clearError,
} = chatSlice.actions;

export default chatSlice.reducer;

// Selectors
export const selectCurrentSession = (state: RootState) => 
  state.chat.currentSessionId ? state.chat.sessions[state.chat.currentSessionId] : null;

export const selectAllSessions = (state: RootState) => 
  Object.values(state.chat.sessions);

export const selectStreamState = (sessionId: string) => (state: RootState) =>
  state.chat.activeStreams[sessionId];
```

### User & Config Slices

```typescript
// store/slices/userSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UserState {
  userId: string | null;
  address: string | null;
  isConnected: boolean;
  preferences: {
    theme: 'light' | 'dark' | 'system';
    fontSize: 'small' | 'medium' | 'large';
    soundEnabled: boolean;
  };
}

const userSlice = createSlice({
  name: 'user',
  initialState: {
    userId: null,
    address: null,
    isConnected: false,
    preferences: {
      theme: 'system',
      fontSize: 'medium',
      soundEnabled: true,
    },
  } as UserState,
  reducers: {
    setUser: (state, action: PayloadAction<{ userId: string; address?: string }>) => {
      state.userId = action.payload.userId;
      state.address = action.payload.address || null;
      state.isConnected = true;
    },
    disconnect: (state) => {
      state.userId = null;
      state.address = null;
      state.isConnected = false;
    },
    updatePreferences: (state, action: PayloadAction<Partial<UserState['preferences']>>) => {
      state.preferences = { ...state.preferences, ...action.payload };
    },
  },
});

// store/slices/configSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ConfigState {
  selectedModelId: string;
  selectedDomainId: string;
  selectedPersonaId: string;
  isMemoryEnabled: boolean;
  models: ModelConfig[];
  domains: DomainConfig[];
  personas: PersonaConfig[];
}

const configSlice = createSlice({
  name: 'config',
  initialState: {
    selectedModelId: 'deepseek-r1',
    selectedDomainId: 'general',
    selectedPersonaId: 'default',
    isMemoryEnabled: false,
    models: [],
    domains: [],
    personas: [],
  } as ConfigState,
  reducers: {
    selectModel: (state, action: PayloadAction<string>) => {
      state.selectedModelId = action.payload;
    },
    selectDomain: (state, action: PayloadAction<string>) => {
      state.selectedDomainId = action.payload;
    },
    selectPersona: (state, action: PayloadAction<string>) => {
      state.selectedPersonaId = action.payload;
    },
    toggleMemory: (state) => {
      state.isMemoryEnabled = !state.isMemoryEnabled;
    },
    loadConfigurations: (state, action) => {
      state.models = action.payload.models;
      state.domains = action.payload.domains;
      state.personas = action.payload.personas;
    },
  },
});
```

### Custom Hooks for Redux

```typescript
// hooks/redux.ts
import { useDispatch, useSelector, TypedUseSelectorHook } from 'react-redux';
import type { RootState, AppDispatch } from '@/store';

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

// hooks/useChat.ts
import { useCallback, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import { 
  selectCurrentSession, 
  createSession, 
  addMessage,
  sendMessage 
} from '@/store/slices/chatSlice';

export function useChat() {
  const dispatch = useAppDispatch();
  const currentSession = useAppSelector(selectCurrentSession);
  const isResearchMode = useAppSelector(state => state.chat.ui.isResearchMode);
  const selectedModelId = useAppSelector(state => state.config.selectedModelId);

  const handleSendMessage = useCallback(async (content: string) => {
    if (!currentSession) {
      // Create new session if needed
      const sessionId = crypto.randomUUID();
      dispatch(createSession({ id: sessionId, name: 'New Chat' }));
    }

    const sessionId = currentSession?.id || crypto.randomUUID();
    
    // Add user message
    dispatch(addMessage({
      sessionId,
      message: {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        timestamp: Date.now(),
      },
    }));

    // Send to API
    await dispatch(sendMessage({
      sessionId,
      message: content,
      modelId: selectedModelId,
    }));
  }, [currentSession, selectedModelId, dispatch]);

  return {
    currentSession,
    isResearchMode,
    sendMessage: handleSendMessage,
  };
}
```

## 2. Dependency Injection Foundation

### Container Setup

```typescript
// services/container/types.ts
export const TYPES = {
  // Services
  TaskService: Symbol.for('TaskService'),
  ResearchService: Symbol.for('ResearchService'),
  QueueService: Symbol.for('QueueService'),
  StreamService: Symbol.for('StreamService'),
  ModelService: Symbol.for('ModelService'),
  
  // Repositories
  SessionRepository: Symbol.for('SessionRepository'),
  MessageRepository: Symbol.for('MessageRepository'),
  
  // External
  WebSocketClient: Symbol.for('WebSocketClient'),
  HttpClient: Symbol.for('HttpClient'),
  Logger: Symbol.for('Logger'),
  EventBus: Symbol.for('EventBus'),
};

// services/container/index.ts
import 'reflect-metadata';
import { Container } from 'inversify';
import { TYPES } from './types';

const container = new Container({
  defaultScope: 'Singleton',
  autoBindInjectable: true,
});

// Bind interfaces to implementations
container.bind<ILogger>(TYPES.Logger).to(ConsoleLogger);
container.bind<IEventBus>(TYPES.EventBus).to(EventBus);
container.bind<IHttpClient>(TYPES.HttpClient).to(AxiosHttpClient);

// Services with dependencies
container.bind<ITaskService>(TYPES.TaskService).to(TaskService);
container.bind<IResearchService>(TYPES.ResearchService).to(ResearchService);
container.bind<IStreamService>(TYPES.StreamService).to(StreamService);

export { container };
```

### Service Interfaces

```typescript
// services/interfaces/ITaskService.ts
export interface ITaskService {
  submitTask(task: TaskRequest): Promise<TaskResponse>;
  getTaskStatus(taskId: string): Promise<TaskStatus>;
  cancelTask(taskId: string): Promise<void>;
  onTaskComplete(callback: (task: Task) => void): Unsubscribe;
}

// services/interfaces/IStreamService.ts
export interface IStreamService {
  createStream(endpoint: string, params: StreamParams): StreamHandle;
  processChunk(streamId: string, chunk: string): void;
  endStream(streamId: string): void;
  getStreamState(streamId: string): StreamState | null;
}

// services/interfaces/IResearchService.ts
export interface IResearchService {
  startResearch(query: string, options: ResearchOptions): Promise<ResearchSession>;
  getResearchStatus(sessionId: string): ResearchStatus;
  streamResults(sessionId: string): AsyncGenerator<ResearchUpdate>;
  stopResearch(sessionId: string): Promise<void>;
}
```

### Service Implementations

```typescript
// services/implementations/TaskService.ts
import { injectable, inject } from 'inversify';
import { TYPES } from '../container/types';

@injectable()
export class TaskService implements ITaskService {
  private taskQueue: Map<string, TaskQueueItem> = new Map();
  private listeners: Set<TaskListener> = new Set();

  constructor(
    @inject(TYPES.HttpClient) private http: IHttpClient,
    @inject(TYPES.EventBus) private eventBus: IEventBus,
    @inject(TYPES.Logger) private logger: ILogger,
  ) {
    this.setupEventListeners();
  }

  async submitTask(task: TaskRequest): Promise<TaskResponse> {
    try {
      this.logger.info('Submitting task', { task });
      
      const response = await this.http.post<TaskResponse>('/api/tasks', task);
      
      // Track task
      this.taskQueue.set(response.taskId, {
        id: response.taskId,
        status: 'pending',
        createdAt: Date.now(),
      });

      // Emit event
      this.eventBus.emit('task:submitted', response);

      return response;
    } catch (error) {
      this.logger.error('Failed to submit task', error);
      throw new TaskSubmissionError('Failed to submit task', error);
    }
  }

  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const cached = this.taskQueue.get(taskId);
    if (cached && cached.status === 'completed') {
      return cached.status;
    }

    const response = await this.http.get<TaskStatusResponse>(`/api/tasks/${taskId}`);
    
    // Update cache
    if (this.taskQueue.has(taskId)) {
      this.taskQueue.set(taskId, {
        ...this.taskQueue.get(taskId)!,
        status: response.status,
      });
    }

    return response.status;
  }

  onTaskComplete(callback: (task: Task) => void): Unsubscribe {
    const listener: TaskListener = { callback };
    this.listeners.add(listener);

    return () => {
      this.listeners.delete(listener);
    };
  }

  private setupEventListeners(): void {
    this.eventBus.on('task:completed', (task: Task) => {
      this.listeners.forEach(listener => listener.callback(task));
    });
  }
}
```

### React Integration

```typescript
// context/ServiceContext.tsx
import { createContext, useContext, ReactNode } from 'react';
import { Container } from 'inversify';
import { container } from '@/services/container';

const ServiceContext = createContext<Container | null>(null);

export function ServiceProvider({ children }: { children: ReactNode }) {
  return (
    <ServiceContext.Provider value={container}>
      {children}
    </ServiceContext.Provider>
  );
}

export function useService<T>(serviceIdentifier: symbol): T {
  const container = useContext(ServiceContext);
  if (!container) {
    throw new Error('useService must be used within ServiceProvider');
  }
  return container.get<T>(serviceIdentifier);
}

// Usage in components
function ChatComponent() {
  const taskService = useService<ITaskService>(TYPES.TaskService);
  const streamService = useService<IStreamService>(TYPES.StreamService);

  const handleSubmit = async (message: string) => {
    const task = await taskService.submitTask({
      type: 'chat',
      payload: { message },
    });
    
    // Handle response...
  };
}
```

## 3. Error Handling Foundation

### Error Classes Hierarchy

```typescript
// errors/AppError.ts
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

// errors/ValidationError.ts
export class ValidationError extends AppError {
  constructor(message: string, details?: unknown) {
    super('VALIDATION_ERROR', message, 400, details);
  }
}

// errors/AuthenticationError.ts
export class AuthenticationError extends AppError {
  constructor(message: string = 'Authentication required') {
    super('AUTHENTICATION_ERROR', message, 401);
  }
}

// errors/NetworkError.ts
export class NetworkError extends AppError {
  constructor(message: string, details?: unknown) {
    super('NETWORK_ERROR', message, 503, details);
  }
}

// errors/StreamError.ts
export class StreamError extends AppError {
  constructor(message: string, public readonly streamId: string) {
    super('STREAM_ERROR', message, 500, { streamId });
  }
}
```

### React Error Boundary

```typescript
// components/ErrorBoundary.tsx
import { Component, ErrorInfo, ReactNode } from 'react';
import { AppError } from '@/errors/AppError';

interface Props {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to monitoring service
    if (error instanceof AppError) {
      console.error('Application error:', {
        ...error.toJSON(),
        componentStack: errorInfo.componentStack,
      });
    } else {
      console.error('Unexpected error:', {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
      });
    }

    // Call custom error handler
    this.props.onError?.(error, errorInfo);

    // Send to monitoring in production
    if (process.env.NODE_ENV === 'production') {
      this.sendToMonitoring(error, errorInfo);
    }
  }

  private sendToMonitoring(error: Error, errorInfo: ErrorInfo) {
    // Integration with Sentry, DataDog, etc.
    if (typeof window !== 'undefined' && window.Sentry) {
      window.Sentry.captureException(error, {
        contexts: {
          react: {
            componentStack: errorInfo.componentStack,
          },
        },
      });
    }
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleReset);
      }

      return <DefaultErrorFallback error={this.state.error} onReset={this.handleReset} />;
    }

    return this.props.children;
  }
}

// components/DefaultErrorFallback.tsx
function DefaultErrorFallback({ error, onReset }: { error: Error; onReset: () => void }) {
  const isAppError = error instanceof AppError;

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
      <div className="max-w-md w-full bg-red-50 border border-red-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-red-800 mb-2">
          {isAppError ? 'Something went wrong' : 'Unexpected error'}
        </h2>
        
        <p className="text-sm text-red-600 mb-4">
          {error.message}
        </p>

        {isAppError && error.code && (
          <p className="text-xs text-red-500 font-mono mb-4">
            Error Code: {error.code}
          </p>
        )}

        <div className="flex gap-2">
          <button
            onClick={onReset}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Try Again
          </button>
          
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
          >
            Refresh Page
          </button>
        </div>
      </div>
    </div>
  );
}
```

### Global Error Handler

```typescript
// middleware/errorHandler.ts
import { NextRequest, NextResponse } from 'next/server';
import { AppError } from '@/errors/AppError';

export function withErrorHandler(
  handler: (req: NextRequest) => Promise<NextResponse>
) {
  return async (req: NextRequest) => {
    try {
      return await handler(req);
    } catch (error) {
      console.error('API Error:', error);

      if (error instanceof AppError) {
        return NextResponse.json(
          {
            error: {
              id: error.id,
              code: error.code,
              message: error.message,
              details: error.details,
            },
          },
          { status: error.statusCode }
        );
      }

      // Unknown errors
      const errorId = crypto.randomUUID();
      console.error(`Unknown error [${errorId}]:`, error);

      return NextResponse.json(
        {
          error: {
            id: errorId,
            code: 'INTERNAL_SERVER_ERROR',
            message: 'An unexpected error occurred',
          },
        },
        { status: 500 }
      );
    }
  };
}

// Usage in API routes
export const POST = withErrorHandler(async (req: NextRequest) => {
  const body = await req.json();
  
  // Validation
  if (!body.message) {
    throw new ValidationError('Message is required');
  }

  // Business logic...
  
  return NextResponse.json({ success: true });
});
```

## 4. Logging Foundation

```typescript
// services/logger/Logger.ts
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
      console.error(this.format('ERROR', message, context), error);
      
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
    // Integration with monitoring service
  }
}
```

## Usage Example

Here's how all these foundations work together:

```typescript
// app/providers.tsx
import { Provider } from 'react-redux';
import { store } from '@/store';
import { ServiceProvider } from '@/context/ServiceContext';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary>
      <Provider store={store}>
        <ServiceProvider>
          {children}
        </ServiceProvider>
      </Provider>
    </ErrorBoundary>
  );
}

// app/chat/page.tsx
import { useChat } from '@/hooks/useChat';
import { useService } from '@/context/ServiceContext';
import { TYPES } from '@/services/container/types';

export default function ChatPage() {
  const { currentSession, sendMessage } = useChat();
  const streamService = useService<IStreamService>(TYPES.StreamService);
  
  const handleSubmit = async (message: string) => {
    try {
      await sendMessage(message);
    } catch (error) {
      if (error instanceof ValidationError) {
        // Handle validation error
        toast.error(error.message);
      } else {
        // Re-throw to be caught by error boundary
        throw error;
      }
    }
  };

  return (
    <div>
      {/* UI Components */}
    </div>
  );
}
```

## Benefits of This Foundation

1. **Centralized State**: All state in Redux, no prop drilling
2. **Type Safety**: Full TypeScript support with proper types
3. **Testability**: All services are injectable and mockable
4. **Error Handling**: Consistent error handling across the app
5. **Monitoring**: Built-in logging and error tracking
6. **Performance**: Optimized re-renders with Redux selectors
7. **Maintainability**: Clear separation of concerns
8. **Scalability**: Easy to add new features and services

## Migration Path

1. **Phase 1**: Set up Redux store alongside existing code
2. **Phase 2**: Add dependency injection for new services
3. **Phase 3**: Wrap app with error boundaries
4. **Phase 4**: Gradually migrate existing hooks to Redux
5. **Phase 5**: Refactor services to use DI
6. **Phase 6**: Remove old implementations

This foundation provides a solid base for building a scalable, maintainable application while allowing incremental migration from the existing codebase.