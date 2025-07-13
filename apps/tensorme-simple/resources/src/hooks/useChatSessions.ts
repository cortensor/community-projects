"use client";

import { useState, useEffect, useCallback, useMemo } from 'react';
import { ChatSession, Message } from '@/types';
import { createNewChatSession } from '@/lib/constants';
import { getFromLocalStorage, saveToLocalStorage } from '@/lib/localStorage';
import { fetchGeneratedTitle } from '@/services/cortensorService';
import { getTaskResult } from '@/services/queueService';
import { cleanBotResponse, generateId } from '@/lib/utils';
import { createPublicClient, http } from 'viem';
import { config } from '@/lib/config';

export const useChatSessions = (userId: string | null) => {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);

  const publicClient = useMemo(() => {
    return createPublicClient({
      chain: config.chain,
      transport: http(config.rpc.http),
    });
  }, []);

  useEffect(() => {
    if (chatSessions.length > 0) {
      saveToLocalStorage('chatSessions', chatSessions);
    }
  }, [chatSessions]);

  useEffect(() => {
    if (currentChatId) {
      saveToLocalStorage('currentChatId', currentChatId);
    }
  }, [currentChatId]);

  const getCurrentChatSession = useCallback(() => {
    return chatSessions.find(s => s.id === currentChatId) || null;
  }, [chatSessions, currentChatId]);

  const handleNewChat = useCallback(() => {
    if (!userId) return '';
    const newSessionName = `Chat ${chatSessions.filter(s => s.owner === userId).length + 1}`;
    const newSession = createNewChatSession(newSessionName, userId);
    setChatSessions(prevSessions => [newSession, ...prevSessions].sort((a, b) => b.timestamp - a.timestamp));
    setCurrentChatId(newSession.id);
    return newSession.id;
  }, [chatSessions, userId]);

  const handleSelectChat = useCallback((chatId: string) => {
    setCurrentChatId(chatId);
  }, []);


  const reconcilePendingTasks = useCallback(async (sessions: ChatSession[]) => {
    // First, set loading state for sessions with pending tasks
    setChatSessions((s) => s.map(session => {
      if (session.lastTaskId !== undefined && session.lastSessionId !== undefined) {
        return { ...session, isLoading: true };
      }
      return session;
    }));

    // Wait for the state update to complete
    await new Promise(resolve => setTimeout(resolve, 100));

    // Then process the sessions
    const reconciledSessions = await Promise.all(
      sessions.map(async (session) => {
        const lastMessage = session.messages[session.messages.length - 1];
        console.log(session.lastTaskId, session.lastSessionId, session.isLoading);

        if (session.isLoading && session.lastTaskId !== undefined && session.lastSessionId !== undefined) {
          const [miners, results] = await getTaskResult(session.lastSessionId?.toString() || '', session.lastTaskId?.toString() || '', publicClient);
          console.log('miners', miners, results);

          if (results !== null) {
            const responses = results.map((result, index) => ({ content: cleanBotResponse(result), minerAddress: miners[index] }));
            const updatedMessages = {
              id: generateId(),
              role: 'assistant',
              content: responses[0].content,
              status: 'ended' as const,
              responses: responses,
              selectedResponseIndex: 0
            }
            return { ...session, messages: [...session.messages, updatedMessages], isLoading: false, lastTaskId: undefined, lastSessionId: undefined };
          }
        }

        return { ...session, isLoading: false };
      })
    );

    // Finally, update with the reconciled sessions
    setChatSessions(reconciledSessions as ChatSession[]);
  }, [publicClient]);

  useEffect(() => {
    if (!userId) return;
    console.log(
      "Is the RPC URL available on the client?",
      process.env
    );

    const savedSessions = getFromLocalStorage<ChatSession[]>('chatSessions', []);
    if (savedSessions.length > 0) {
      reconcilePendingTasks(savedSessions);
    } else {
      const userSession = createNewChatSession('My First Chat', userId);
      setChatSessions([userSession]);
    }
  }, [userId, reconcilePendingTasks]);


  const handleRenameChat = useCallback((chatId: string, newName: string) => {
    const sessionToRename = chatSessions.find(s => s.id === chatId);
    if (sessionToRename?.owner !== userId) return;

    setChatSessions(prevSessions =>
      prevSessions.map(session =>
        session.id === chatId
          ? { ...session, name: newName, timestamp: Date.now() }
          : session
      ).sort((a, b) => b.timestamp - a.timestamp)
    );
  }, [chatSessions, userId]);

  const handleDeleteChat = useCallback((chatIdToDelete: string, event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    const sessionToDelete = chatSessions.find(s => s.id === chatIdToDelete);
    if (sessionToDelete?.owner !== userId) return;

    setChatSessions(prevSessions => {
      const remainingSessions = prevSessions.filter(session => session.id !== chatIdToDelete);
      if (currentChatId === chatIdToDelete) {
        const userChats = remainingSessions.filter(s => s.owner === userId).sort((a, b) => b.timestamp - a.timestamp);
        setCurrentChatId(userChats[0]?.id || (remainingSessions.length > 0 ? remainingSessions[0].id : null));
      }
      return remainingSessions;
    });
  }, [chatSessions, currentChatId, userId]);

  const handleAutoRename = useCallback(async (chatId: string, userMessage: Message, botMessage: Message) => {
    const conversationText = `User: ${userMessage.content}\nAssistant: ${botMessage.content}`;
    try {
      const { title } = await fetchGeneratedTitle(conversationText);
      setChatSessions(prev =>
        prev.map(s =>
          s.id === chatId ? { ...s, name: title } : s
        )
      );
    } catch (renameError) {
      console.error("Could not automatically rename the chat:", renameError);
    }
  }, [chatSessions, setChatSessions, fetchGeneratedTitle]);

  const setLoadingStart = useCallback((chatId: string) => {
    setChatSessions(prev =>
      prev.map(s =>
        s.id === chatId ? { ...s, isLoading: true } : s
      )
    );
  }, []);

  const setLoadingEnd = useCallback((chatId: string) => {
    setChatSessions(prev =>
      prev.map(s =>
        s.id === chatId ? { ...s, isLoading: false } : s
      )
    );
  }, []);

  return {
    chatSessions,
    currentChatId,
    getCurrentChatSession,
    handleNewChat,
    handleSelectChat,
    handleRenameChat,
    handleDeleteChat,
    setChatSessions,
    handleAutoRename,
    setLoadingStart,
    setLoadingEnd,
  };
};