import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { createSelector } from 'reselect';
import { Message, ChatSession, SessionConfig } from '@/types';
import { modelSupportsResearch } from '@/lib/models';

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

// Helper function to determine initial sidebar state based on screen size
const getInitialSidebarState = () => {
  if (typeof window === 'undefined') return false; // SSR default
  return window.innerWidth >= 768; // Desktop default: open, mobile default: closed
};

const initialState: ChatState = {
  sessions: {},
  currentSessionId: null,
  activeStreams: {},
  ui: {
    isSidebarOpen: getInitialSidebarState(),
    isResearchMode: false,
    selectedResponseIndex: {},
  },
  error: null,
};

// Async thunks for complex operations
export const loadChatSessions = createAsyncThunk(
  'chat/loadSessions',
  async (userId: string) => {
    // Load from localStorage
    const stored = localStorage.getItem(`chat_sessions_${userId}`);
    if (stored) {
      return JSON.parse(stored);
    }
    return {};
  }
);

export const saveChatSessions = createAsyncThunk(
  'chat/saveSessions',
  async ({ userId, sessions }: { userId: string; sessions: Record<string, ChatSession> }) => {
    localStorage.setItem(`chat_sessions_${userId}`, JSON.stringify(sessions));
    return sessions;
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
      persona?: string;
    },
    { dispatch, getState }
  ) => {
    // Start streaming
    dispatch(startStream({ sessionId: params.sessionId }));
    
    // Call API
    const response = await fetch('/api/conversation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: (getState() as any).chat.sessions[params.sessionId]?.messages || [],
        persona: params.persona,
        modelId: params.modelId,
        chatId: params.sessionId,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    // Return stream reader for processing
    return response.body?.getReader();
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    // Session management
    createSession: (state, action: PayloadAction<{ id: string;  name: string; owner: string; config?: Partial<SessionConfig> }>) => {
      const defaultConfig: SessionConfig = {
        modelId: 'deepseek-r1',
        domainId: 'general',
        personaId: 'default',
        isMemoryEnabled: false,
        isResearchMode: false,
      };

      state.sessions[action.payload.id] = {
        id: action.payload.id,
        name: action.payload.name,
        messages: [],
        timestamp: Date.now(),
        isLoading: false,
        owner: action.payload.owner,
        config: { ...defaultConfig, ...action.payload.config },
      };
      state.currentSessionId = action.payload.id;
    },

    selectSession: (state, action: PayloadAction<string>) => {
      if (state.sessions[action.payload]) {
        state.currentSessionId = action.payload;
      }
    },

    deleteSession: (state, action: PayloadAction<string>) => {
      if (state.sessions[action.payload]) {
        delete state.sessions[action.payload];
        // If deleted session was current, select another or set to null
        if (state.currentSessionId === action.payload) {
          const remainingSessions = Object.keys(state.sessions);
          state.currentSessionId = remainingSessions.length > 0 ? remainingSessions[0] : null;
        }
      }
    },

    renameSession: (state, action: PayloadAction<{ id: string; name: string }>) => {
      if (state.sessions[action.payload.id]) {
        state.sessions[action.payload.id].name = action.payload.name;
      }
    },

    updateSession: (state, action: PayloadAction<{ sessionId: string; updates: Partial<ChatSession> }>) => {
      const session = state.sessions[action.payload.sessionId];
      if (session) {
        Object.assign(session, action.payload.updates);
      }
    },

    // Message management
    addMessage: (state, action: PayloadAction<{ sessionId: string; message: Message }>) => {
      const session = state.sessions[action.payload.sessionId];
      if (session) {
        session.messages.push(action.payload.message);
        session.timestamp = Date.now();
      }
    },

    updateMessage: (state, action: PayloadAction<{ sessionId: string; messageId: string; updates: Partial<Message> }>) => {
      const session = state.sessions[action.payload.sessionId];
      if (session) {
        const messageIndex = session.messages.findIndex(msg => msg.id === action.payload.messageId);
        if (messageIndex !== -1) {
          session.messages[messageIndex] = {
            ...session.messages[messageIndex],
            ...action.payload.updates,
          };
        }
      }
    },

    selectResponse: (state, action: PayloadAction<{ messageId: string; responseIndex: number }>) => {
      state.ui.selectedResponseIndex[action.payload.messageId] = action.payload.responseIndex;
    },

    // Stream management
    startStream: (state, action: PayloadAction<{ sessionId: string }>) => {
      state.activeStreams[action.payload.sessionId] = {
        buffer: '',
        isStreaming: true,
        startTime: Date.now(),
        chunks: [],
      };
      
      // Set session as loading
      if (state.sessions[action.payload.sessionId]) {
        state.sessions[action.payload.sessionId].isLoading = true;
      }
    },

    appendStreamChunk: (state, action: PayloadAction<{ sessionId: string; chunk: string }>) => {
      const stream = state.activeStreams[action.payload.sessionId];
      if (stream) {
        stream.buffer += action.payload.chunk;
        stream.chunks.push(action.payload.chunk);
        
        // Update the last assistant message with current buffer
        const session = state.sessions[action.payload.sessionId];
        if (session) {
          const lastMessage = session.messages[session.messages.length - 1];
          if (lastMessage && lastMessage.role === 'assistant') {
            lastMessage.content = stream.buffer;
          }
        }
      }
    },

    endStream: (state, action: PayloadAction<{ sessionId: string; finalContent?: string }>) => {
      const stream = state.activeStreams[action.payload.sessionId];
      if (stream) {
        stream.isStreaming = false;
        
        // Update final message content
        const session = state.sessions[action.payload.sessionId];
        if (session) {
          const lastMessage = session.messages[session.messages.length - 1];
          if (lastMessage && lastMessage.role === 'assistant') {
            lastMessage.content = action.payload.finalContent || stream.buffer;
          }
          session.isLoading = false;
        }
        
        // Clean up stream
        delete state.activeStreams[action.payload.sessionId];
      }
    },

    // UI state
    toggleSidebar: (state) => {
      state.ui.isSidebarOpen = !state.ui.isSidebarOpen;
    },

    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.ui.isSidebarOpen = action.payload;
    },

    toggleResearchMode: (state) => {
      state.ui.isResearchMode = !state.ui.isResearchMode;
    },

    setResearchMode: (state, action: PayloadAction<boolean>) => {
      state.ui.isResearchMode = action.payload;
    },

    // Responsive sidebar actions
    initializeSidebar: (state) => {
      state.ui.isSidebarOpen = getInitialSidebarState();
    },

    updateSidebarForScreenSize: (state, action: PayloadAction<{ width: number }>) => {
      const isDesktop = action.payload.width >= 768;
      state.ui.isSidebarOpen = isDesktop;
    },

    // Session-specific configuration actions
    updateSessionConfig: (state, action: PayloadAction<{ sessionId: string; config: Partial<SessionConfig> }>) => {
      const session = state.sessions[action.payload.sessionId];
      if (session) {
        session.config = { ...session.config, ...action.payload.config };
      }
    },
    
    setSessionModel: (state, action: PayloadAction<{ sessionId: string; modelId: string }>) => {
      const session = state.sessions[action.payload.sessionId];
      if (session) {
        session.config.modelId = action.payload.modelId;
      }
    },
    
    setSessionDomain: (state, action: PayloadAction<{ sessionId: string; domainId?: string }>) => {
      const session = state.sessions[action.payload.sessionId];
      if (session) {
        session.config.domainId = action.payload.domainId;
      }
    },
    
    setSessionPersona: (state, action: PayloadAction<{ sessionId: string; personaId?: string }>) => {
      const session = state.sessions[action.payload.sessionId];
      if (session) {
        session.config.personaId = action.payload.personaId;
      }
    },
    
    toggleSessionMemory: (state, action: PayloadAction<{ sessionId: string }>) => {
      const session = state.sessions[action.payload.sessionId];
      if (session) {
        session.config.isMemoryEnabled = !session.config.isMemoryEnabled;
      }
    },
    
    toggleSessionResearch: (state, action: PayloadAction<{ sessionId: string }>) => {
      const session = state.sessions[action.payload.sessionId];
      if (session) {
        session.config.isResearchMode = !session.config.isResearchMode;
      }
    },

    // Error handling
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
  deleteSession,
  renameSession,
  updateSession,
  addMessage,
  updateMessage,
  selectResponse,
  startStream,
  appendStreamChunk,
  endStream,
  toggleSidebar,
  setSidebarOpen,
  toggleResearchMode,
  setResearchMode,
  initializeSidebar,
  updateSidebarForScreenSize,
  updateSessionConfig,
  setSessionModel,
  setSessionDomain,
  setSessionPersona,
  toggleSessionMemory,
  toggleSessionResearch,
  setError,
  clearError,
} = chatSlice.actions;

export default chatSlice.reducer;

// Basic selectors (input selectors)
const selectChatState = (state: { chat: ChatState }) => state.chat;
const selectSessions = (state: { chat: ChatState }) => state.chat.sessions;
const selectCurrentSessionId = (state: { chat: ChatState }) => state.chat.currentSessionId;
const selectUIState = (state: { chat: ChatState }) => state.chat.ui;

// Memoized selectors for derived data
export const selectCurrentSession = createSelector(
  [selectSessions, selectCurrentSessionId],
  (sessions, currentSessionId) => 
    currentSessionId ? sessions[currentSessionId] : null
);

export const selectAllSessions = createSelector(
  [selectSessions],
  (sessions) => Object.values(sessions).sort((a, b) => b.timestamp - a.timestamp)
);

export const selectCurrentSessionConfig = createSelector(
  [selectCurrentSession],
  (session) => session?.config || null
);

export const selectSessionMessages = createSelector(
  [selectCurrentSession],
  (session) => session?.messages || []
);

// Selector factory for parameterized selectors
export const makeSelectSessionsByOwner = () => 
  createSelector(
    [selectAllSessions, (state: { chat: ChatState }, owner: string) => owner],
    (sessions, owner) => sessions.filter(session => session.owner === owner)
  );

// UI-related memoized selectors
export const selectIsSidebarOpen = createSelector(
  [selectUIState],
  (ui) => ui.isSidebarOpen
);

export const selectIsResearchMode = createSelector(
  [selectUIState],
  (ui) => ui.isResearchMode
);

// Stream-related selector factory
export const makeSelectStreamState = (sessionId: string) => 
  createSelector(
    [selectChatState],
    (chatState) => chatState.activeStreams[sessionId]
  );

export const selectActiveStreamCount = createSelector(
  [selectChatState],
  (chatState) => Object.keys(chatState.activeStreams).length
);

// Session config derived selectors
export const selectCurrentSessionModelId = createSelector(
  [selectCurrentSessionConfig],
  (config) => config?.modelId || 'deepseek-r1'
);

export const selectCurrentSessionDomainId = createSelector(
  [selectCurrentSessionConfig],
  (config) => config?.domainId
);

export const selectCurrentSessionPersonaId = createSelector(
  [selectCurrentSessionConfig],
  (config) => config?.personaId
);

export const selectCurrentSessionMemoryEnabled = createSelector(
  [selectCurrentSessionConfig],
  (config) => config?.isMemoryEnabled || false
);

export const selectCurrentSessionResearchMode = createSelector(
  [selectCurrentSessionConfig],
  (config) => config?.isResearchMode || false
);

// Complex derived selectors for counts and statistics
export const selectSessionCount = createSelector(
  [selectAllSessions],
  (sessions) => sessions.length
);

export const selectRecentSessions = createSelector(
  [selectAllSessions],
  (sessions) => sessions.slice(0, 10) // Most recent 10 sessions
);

export const selectSessionsWithMessages = createSelector(
  [selectAllSessions],
  (sessions) => sessions.filter(session => session.messages.length > 0)
);

// Derived state selectors
export const selectCurrentSessionSupportsResearch = createSelector(
  [selectCurrentSessionConfig],
  (config) => config?.modelId ? modelSupportsResearch(config.modelId) : false
);