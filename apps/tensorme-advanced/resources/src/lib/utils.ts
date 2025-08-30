import { Message } from "@/types";

export const generateId = (): string => crypto.randomUUID();

export function safeJsonParse<T>(jsonString: string): T | { raw: string } {
  try {
    return JSON.parse(jsonString) as T;
  } catch {
    return { raw: jsonString };
  }
}

export const cleanBotResponse = (text: string): string => {
  const assistantMarker = 'Assistant: ';
  const lastIndex = text.lastIndexOf(assistantMarker);

  let cleanedText = text;
  if (lastIndex !== -1) {
    cleanedText = text.substring(lastIndex + assistantMarker.length);
  }

  cleanedText = cleanedText.replace(/<[^>]*>/g, '').trim();
  const prefixes = ["Cortensor:", "Assistant:", "Eliza:"];
  for (const prefix of prefixes) {
    if (cleanedText.startsWith(prefix)) {
      cleanedText = cleanedText.substring(prefix.length).trim();
    }
  }

  return cleanedText;
};

export const limitConversationHistory = (messages: Message[], maxMessages: number = 10): Message[] => {
  if (messages.length <= maxMessages) {
    return messages;
  }

  const recentMessages = messages.slice(-maxMessages);

  if (recentMessages[0]?.role === 'assistant') {
    return recentMessages.slice(1);
  }

  return recentMessages;
};

export const getRecentMessages = (messages: Message[], maxMessages: number = 30): Message[] => {
  return messages.slice(-maxMessages);
};

export const getFullMessagesFromStorage = (sessionId: string): Message[] => {
  try {
    const stored = localStorage.getItem(`chat_full_${sessionId}`);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

export const saveFullMessagesToStorage = (sessionId: string, messages: Message[]): void => {
  try {
    localStorage.setItem(`chat_full_${sessionId}`, JSON.stringify(messages));
  } catch (error) {
    console.error('Failed to save full messages to storage:', error);
  }
};

export const loadOlderMessages = (sessionId: string, currentMessages: Message[], loadCount: number = 20): Message[] => {
  const fullMessages = getFullMessagesFromStorage(sessionId);
  const currentFirstId = currentMessages[0]?.id;

  if (!currentFirstId || fullMessages.length === 0) {
    return currentMessages;
  }

  const currentFirstIndex = fullMessages.findIndex(msg => msg.id === currentFirstId);

  if (currentFirstIndex <= 0) {
    return currentMessages;
  }

  const startIndex = Math.max(0, currentFirstIndex - loadCount);
  const olderMessages = fullMessages.slice(startIndex, currentFirstIndex);

  return [...olderMessages, ...currentMessages];
};