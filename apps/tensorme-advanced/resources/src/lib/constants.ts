import { Message, ChatSession } from '@/types';
import { generateId } from './utils';

export const SYSTEM_OWNER_ID = 'system';

export const initialWelcomeMessage: Message = {
  id: generateId(),
  role: 'assistant',
  content: 'Welcome! I am your Cortensor AI assistant.',
};

export const createNewChatSession = (name?: string, owner?: string): ChatSession => ({
  id: generateId(),
  name: name || `Chat ${Date.now().toString().slice(-4)}`,
  messages: [],
  timestamp: Date.now(),
  owner: owner || SYSTEM_OWNER_ID,
  config: {
    modelId: 'deepseek-r1',
    isMemoryEnabled: false,
    isResearchMode: false,
  }
});