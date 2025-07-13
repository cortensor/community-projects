"use client";

import { useState, useRef, useEffect } from 'react';
import { ChatSession, Message } from '@/types';
import { generateId } from '@/lib/utils';
import { fetchWeb3Completion } from '@/services/cortensorService';
import { Persona } from '@/hooks/usePersonas';
import { useUser } from '@/hooks/useUser';

interface ErrorState {
  chatId: string;
  message: string;
}

interface SubmitOptions {
  chatId?: string;
}

export const useChatCompletion = (
  chatSessions: ChatSession[],
  currentChatId: string | null,
  setChatSessions: React.Dispatch<React.SetStateAction<ChatSession[]>>,
  selectedPersona: Persona | undefined,
  isMemoryEnabled: boolean,
) => {

  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState<ErrorState | null>(null);

  const { userId } = useUser();

  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (inputRef.current) inputRef.current.focus();
  }, [currentChatId]);

  useEffect(() => {
    setError(null);
  }, [currentChatId]);

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
      setChatSessions(prevSessions =>
        prevSessions.map(session =>
          session.id === chatIdToUse
            ? { ...session, isLoading: false, messages: [...session.messages], timestamp: Date.now() }
            : session
        )
      );
      return;
    }

    setChatSessions(prevSessions =>
      prevSessions.map(session =>
        session.id === chatIdToUse
          ? { ...session, isLoading: true, loadingMessage: "Assistant is thinking..." }
          : session
      )
    );

    setChatSessions(prevSessions =>
      prevSessions.map(session =>
        session.id === chatIdToUse
          ? { ...session, messages: [...session.messages, userMessage], timestamp: Date.now() }
          : session
      )
    );

    try {
      const messagesForApi = isMemoryEnabled
        ? [...sessionForSubmit.messages, userMessage]
        : [userMessage];

      await fetchWeb3Completion(
        messagesForApi,
        selectedPersona?.description,
        chatIdToUse,
        clientReference,
        userId || ''
      );

    } catch (err: any) {
      const errorMessage = err.message || 'Failed to connect to the AI.';
      setError({ chatId: chatIdToUse, message: errorMessage });

      setInputValue(trimmedInput);

      setChatSessions(prevSessions =>
        prevSessions.map(session =>
          session.id === chatIdToUse
            ? {
              ...session,
              isLoading: false,
              loadingMessage: undefined,
              messages: session.messages.filter(msg =>
                msg.id !== userMessage.id && msg.clientReference !== userMessage.clientReference
              ),
            }
            : session
        )
      );
    } finally {
    }
  };

  const handleSelectResponse = (messageId: string, newIndex: number) => {
    console.log("handleSelectResponse", messageId, newIndex);
    setChatSessions(prevSessions =>
      prevSessions.map(session => ({
        ...session,
        messages: session.messages.map(msg => {
          if (msg.id === messageId && msg.responses) {
            console.log("msg", msg.responses);
          }
          if (msg.id === messageId && msg.responses && msg.responses[newIndex]) {
            return {
              ...msg,
              selectedResponseIndex: newIndex,
              content: msg.responses[newIndex].content,
            };
          }
          return msg;
        }),
      }))
    );
  };

  return {
    inputValue,
    error,
    inputRef,
    messagesEndRef,
    handleInputChange,
    handleSubmit,
    handleSelectResponse,
  };
};