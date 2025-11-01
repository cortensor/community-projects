"use client";

import { useState, useRef, useEffect } from 'react';
import { ChatSession, Message } from '@/types';
import { generateId, limitConversationHistory } from '@/lib/utils';
import { Persona } from '@/hooks/usePersonas';
import { Model } from '@/hooks/useModels';
import { useUser } from '@/hooks/useUser';
import { useModelStreamProcessor } from '@/hooks/useModelStreamProcessor';
import { modelSupportsResearch } from '@/lib/models';
import { DomainConfig } from '@/lib/domains';
import { useAppDispatch } from './redux';
import { addMessage, updateMessage, startStream, endStream, selectResponse } from '@/store/slices/chatSlice';

export interface ErrorState {
  chatId: string;
  message: string;
}

interface SubmitOptions {
  chatId?: string;
}

export const useChatCompletion = (
  chatSessions: ChatSession[],
  currentChatId: string | null,
  _setChatSessions: any, // Deprecated parameter, kept for compatibility
  selectedPersona: Persona | undefined,
  selectedModel: Model | undefined,
  selectedDomain: DomainConfig | undefined,
  isMemoryEnabled: boolean,
) => {
  const dispatch = useAppDispatch();

  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState<ErrorState | null>(null);
  const [isResearchMode, setIsResearchMode] = useState(false);
  
  const supportsResearch = modelSupportsResearch(selectedModel?.id);

  const { userId } = useUser();
  const { processStream } = useModelStreamProcessor(setError, selectedModel?.id);

  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (inputRef.current) inputRef.current.focus();
  }, [currentChatId]);

  useEffect(() => {
    setError(null);
  }, [currentChatId]);

  // Disable research mode when switching to a model that doesn't support it
  useEffect(() => {
    if (!supportsResearch && isResearchMode) {
      setIsResearchMode(false);
    }
  }, [selectedModel?.id, supportsResearch, isResearchMode]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>, options: SubmitOptions = {}) => {
    e.preventDefault();
    const trimmedInput = inputValue.trim();
    const chatIdToUse = options.chatId || currentChatId;

    if (!trimmedInput || !chatIdToUse) return;

    setError(null);
    setInputValue('');

    const clientReference = generateId();
    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: trimmedInput,
      clientReference
    };

    const sessionForSubmit = chatSessions.find(session => session.id === chatIdToUse);
    if (!sessionForSubmit) {
      return;
    }

    // Add user message using Redux
    dispatch(addMessage({ sessionId: chatIdToUse, message: userMessage }));
    
    // Start stream (this also sets loading state)
    dispatch(startStream({ sessionId: chatIdToUse }));

    try {
      const messagesForApi = isMemoryEnabled
        ? limitConversationHistory([...sessionForSubmit.messages, userMessage], 10)
        : [userMessage];

      // Choose endpoint based on research mode and model capability
      const endpoint = isResearchMode && supportsResearch
        ? '/api/deepseek-research'
        : '/api/conversation';
      
      // Update loading message for research mode
      if (isResearchMode && supportsResearch) {
        // The loading message will be handled by the stream processor
        // Research mode messages are processed differently
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: messagesForApi,
          persona: selectedPersona?.description,
          domainContext: selectedDomain?.systemPrompt,
          historySummary: sessionForSubmit.historySummary?.trim(),
          clientReference: clientReference,
          userId: userId,
          modelId: selectedModel?.id,
          chatId: chatIdToUse,
        }),
      });

      if (!response.ok || !response.body) {
        const errorData = await response.json().catch(() => ({ message: 'Unknown API error.' }));
        throw new Error(errorData.message || 'Failed to get streaming response.');
      }

      const reader = response.body.getReader();
      await processStream(reader, chatIdToUse);

    } catch (err: any) {
      const errorMessage = (err.message || 'Failed to connect to the AI.') + ' Please retry.';
      setError({ chatId: chatIdToUse, message: errorMessage });

      setInputValue(trimmedInput);

      // End stream and remove user message on error
      dispatch(endStream({ sessionId: chatIdToUse }));
      // Note: We should remove the user message, but for now we'll leave it
      // as the Redux store doesn't have a removeMessage action yet
    } finally {
    }
  };

  const handleSelectResponse = (messageId: string, newIndex: number) => {
    dispatch(selectResponse({ messageId, responseIndex: newIndex }));
    
    // Update message content based on selected response
    const session = chatSessions.find(s => s.id === currentChatId);
    const message = session?.messages.find(m => m.id === messageId);
    if (message?.responses && message.responses[newIndex] && currentChatId) {
      dispatch(updateMessage({
        sessionId: currentChatId,
        messageId,
        updates: {
          selectedResponseIndex: newIndex,
          content: message.responses[newIndex].content,
        }
      }));
    }
  };

  const handleResearchToggle = (enabled: boolean) => {
    // Only allow enabling research mode if the model supports it
    if (enabled && !supportsResearch) {
      return;
    }
    setIsResearchMode(enabled);
  };

  return {
    inputValue,
    error,
    inputRef,
    messagesEndRef,
    isResearchMode,
    supportsResearch,
    handleInputChange,
    handleSubmit,
    handleSelectResponse,
    handleResearchToggle,
  };
};