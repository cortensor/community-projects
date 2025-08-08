// src/lib/storage.ts
import { storageLogger } from './logger';

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  thinkingContent?: string // For DeepSeek thinking process
  timestamp: Date
}

export interface ChatSession {
  id: string // ID lokal untuk UI
  cortensorSessionId: string | null // ID asli dari server Cortensor
  title: string
  messages: ChatMessage[]
  selectedModel: string // Store the model used for this session
  createdAt: Date
  updatedAt: Date
}

export class ChatStorage {
  private static readonly SESSIONS_KEY = "chat_sessions"
  private static readonly MAX_SESSIONS = 50 // Limit sessions to prevent storage overflow
  private static readonly MAX_MESSAGES_PER_SESSION = 100 // Limit messages per session

  static saveSessions(sessions: ChatSession[]): boolean {
    try {
      // Limit number of sessions
      const limitedSessions = sessions.slice(-this.MAX_SESSIONS);
      
      // Limit messages per session
      const optimizedSessions = limitedSessions.map(session => ({
        ...session,
        messages: session.messages.slice(-this.MAX_MESSAGES_PER_SESSION)
      }));

      const serializedSessions = JSON.stringify(optimizedSessions);
      
      // Check if data is too large for localStorage
      if (serializedSessions.length > 4.5 * 1024 * 1024) { // 4.5MB limit
        storageLogger.warn('Sessions data is too large, removing oldest sessions');
        const reducedSessions = optimizedSessions.slice(-Math.floor(this.MAX_SESSIONS / 2));
        const reducedSerialized = JSON.stringify(reducedSessions);
        localStorage.setItem(this.SESSIONS_KEY, reducedSerialized);
      } else {
        localStorage.setItem(this.SESSIONS_KEY, serializedSessions);
      }

      storageLogger.debug('Sessions saved successfully', { count: optimizedSessions.length });
      return true;
    } catch (error) {
      storageLogger.error('Failed to save sessions to local storage', error);
      
      // Try to clear corrupted data and retry with minimal data
      try {
        localStorage.removeItem(this.SESSIONS_KEY);
        const minimalSessions = sessions.slice(-5).map(session => ({
          ...session,
          messages: session.messages.slice(-10)
        }));
        localStorage.setItem(this.SESSIONS_KEY, JSON.stringify(minimalSessions));
        storageLogger.info('Saved minimal sessions after error');
        return true;
      } catch (retryError) {
        storageLogger.error('Failed to save even minimal sessions', retryError);
        return false;
      }
    }
  }

  static loadSessions(): ChatSession[] {
    try {
      const serializedSessions = localStorage.getItem(this.SESSIONS_KEY);
      if (serializedSessions === null) {
        storageLogger.debug('No sessions found in storage');
        return [];
      }

      const parsed = JSON.parse(serializedSessions);
      
      // Validate and transform the data
      const validatedSessions = this.validateAndTransformSessions(parsed);
      
      storageLogger.debug('Sessions loaded successfully', { count: validatedSessions.length });
      return validatedSessions;
    } catch (error) {
      storageLogger.error('Failed to load sessions from local storage', error);
      
      // Try to recover by clearing corrupted data
      try {
        localStorage.removeItem(this.SESSIONS_KEY);
        storageLogger.info('Cleared corrupted session data');
      } catch (clearError) {
        storageLogger.error('Failed to clear corrupted data', clearError);
      }
      
      return [];
    }
  }

  static clearAllSessions(): boolean {
    try {
      localStorage.removeItem(this.SESSIONS_KEY);
      localStorage.removeItem('lastActiveSessionId');
      storageLogger.info('All sessions cleared successfully');
      return true;
    } catch (error) {
      storageLogger.error('Failed to clear sessions', error);
      return false;
    }
  }

  static getStorageInfo(): { used: string; available: string; sessionCount: number } {
    try {
      const sessions = this.loadSessions();
      const serialized = localStorage.getItem(this.SESSIONS_KEY) || '';
      const usedBytes = new Blob([serialized]).size;
      const usedMB = (usedBytes / (1024 * 1024)).toFixed(2);
      
      // Rough estimate of available space
      const totalStorage = 5 * 1024 * 1024; // 5MB typical limit
      const availableMB = ((totalStorage - usedBytes) / (1024 * 1024)).toFixed(2);
      
      return {
        used: `${usedMB} MB`,
        available: `${availableMB} MB`,
        sessionCount: sessions.length
      };
    } catch (error) {
      storageLogger.error('Failed to get storage info', error);
      return { used: 'Unknown', available: 'Unknown', sessionCount: 0 };
    }
  }

  private static validateAndTransformSessions(data: any[]): ChatSession[] {
    if (!Array.isArray(data)) {
      storageLogger.warn('Invalid sessions data format, expected array');
      return [];
    }

    return data
      .filter(session => this.isValidSession(session))
      .map(session => ({
        ...session,
        createdAt: new Date(session.createdAt),
        updatedAt: new Date(session.updatedAt),
        messages: this.validateAndTransformMessages(session.messages)
      }))
      .filter(session => session.messages.length >= 0); // Keep even empty sessions
  }

  private static isValidSession(session: any): boolean {
    return (
      session &&
      typeof session.id === 'string' &&
      typeof session.title === 'string' &&
      Array.isArray(session.messages) &&
      session.createdAt &&
      session.updatedAt
    );
  }

  private static validateAndTransformMessages(messages: any[]): ChatMessage[] {
    if (!Array.isArray(messages)) {
      storageLogger.warn('Invalid messages data format');
      return [];
    }

    return messages
      .filter(msg => this.isValidMessage(msg))
      .map(msg => ({
        ...msg,
        timestamp: new Date(msg.timestamp)
      }));
  }

  private static isValidMessage(message: any): boolean {
    return (
      message &&
      typeof message.id === 'string' &&
      typeof message.content === 'string' &&
      (message.role === 'user' || message.role === 'assistant') &&
      message.timestamp
    );
  }

  // Method to handle storage conflicts during model changes
  static clearStorageConflicts(): boolean {
    try {
      storageLogger.info('Clearing storage conflicts');
      
      // Remove any pending operations
      const keysToClean = [
        'chat-temp-data',
        'pending-model-change',
        'chat-loading-state'
      ];
      
      keysToClean.forEach(key => {
        try {
          localStorage.removeItem(key);
        } catch (error) {
          storageLogger.warn(`Failed to remove ${key}`, error);
        }
      });
      
      return true;
    } catch (error) {
      storageLogger.error('Failed to clear storage conflicts', error);
      return false;
    }
  }

  // Method to force save sessions with conflict resolution
  static forceSaveSessions(sessions: ChatSession[], retryCount = 0): boolean {
    if (retryCount > 2) {
      storageLogger.error('Max retries exceeded for forceSaveSessions');
      return false;
    }

    try {
      // Clear conflicts first
      this.clearStorageConflicts();
      
      // Save with reduced data if necessary
      const result = this.saveSessions(sessions);
      
      if (!result && retryCount < 2) {
        storageLogger.warn('Force save failed, retrying', { retryCount });
        // Wait a bit and retry
        setTimeout(() => {
          this.forceSaveSessions(sessions, retryCount + 1);
        }, 100);
      }
      
      return result;
    } catch (error) {
      storageLogger.error('Force save sessions failed', error);
      return false;
    }
  }
}

