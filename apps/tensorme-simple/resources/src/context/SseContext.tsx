// src/context/SseContext.tsx
"use client";

import React, { createContext, useContext, useEffect, useRef } from 'react';
import { useUser } from '@/hooks/useUser';
import { ChatSession, Message } from '@/types';
import { generateId } from '@/lib/utils';

type SseContextType = undefined;

const SseContext = createContext<SseContextType>(undefined);

export const SseProvider: React.FC<{
  children: React.ReactNode;
  setChatSessions: React.Dispatch<React.SetStateAction<ChatSession[]>>;
}> = ({ children, setChatSessions }) => {
  const { userId } = useUser();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!userId) return;

    let reconnectDelay = 1000;
    const maxReconnectDelay = 30000;

    const connect = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const es = new EventSource(`/api/chat-status/${userId}`);
      eventSourceRef.current = es;

      es.onopen = () => {
        console.log("SSE connection established.");
        reconnectDelay = 1000;
      };

      es.onmessage = (event) => {
        // Ignore heartbeat messages
        if (event.data.startsWith(':')) {
          return;
        }

        const {
          clientReference,
          status,
          content,
          chatId,
          multipleResults,
          ackedCount,
          expectedAckedCount,
          precommitCount,
          expectedPrecommitCount,
          commitCount,
          expectedCommitCount,
          taskId,
          sessionId
        } = JSON.parse(event.data);

        let isLoading = status !== 'ended' && status !== 'error';
        let loadingMessage = undefined;
        switch (status) {
          case 'submitted':
            loadingMessage = "Task submitted, waiting for miner...";
            break;
          case 'assigned':
            loadingMessage = "Task assigned to miner...";
            break;
          case 'acked':
            loadingMessage = `Task acked by miner... (${ackedCount}/${expectedAckedCount})`;
            break;
          case 'precommitted':
            loadingMessage = `Task precommitted by miner... (${precommitCount}/${expectedPrecommitCount})`;
            break;
          case 'all_precommitted':
            loadingMessage = `Task precommitted by all miners...`;
            break;
          case 'committed':
            loadingMessage = `Task committed by miner... (${commitCount}/${expectedCommitCount})`;
            break;
          case 'all_committed':
            loadingMessage = `Task committed by all miners...`;
            break;
          case 'ended':
            isLoading = false;
            loadingMessage = undefined;
            break;
          default:
            isLoading = true;
            loadingMessage = "Task is processing...";
            break;
        }

        setChatSessions(prevSessions =>
          prevSessions.map(session => (
            session.id === chatId
              ? { ...session, isLoading, loadingMessage, lastTaskId: taskId, lastSessionId: sessionId }
              : session
          ))
        );


        if (status === 'ended' || status === 'error') {
          const botMessage: Message = {
            id: generateId(),
            role: 'assistant',
            content: content || '',
            clientReference,
            status: 'ended',
            responses: multipleResults ? multipleResults.split('---newline-content-separator---').map((result: string) => {
              const [content, minerAddress] = result.split('---single-content-separator---');
              return {
                content,
                minerAddress
              };
            }) : undefined,
            selectedResponseIndex: 0
          };

          if (status === 'error') {
            botMessage.isError = true;
          }
          setChatSessions(prevSessions =>
            prevSessions.map(session => (
              session.id === chatId
                ? { ...session, messages: [...session.messages, botMessage] }
                : session
            ))
          );
        }

      };

      es.onerror = (err) => {
        console.error("EventSource failed:", err);
        es.close();

        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectDelay = Math.min(maxReconnectDelay, reconnectDelay * 2);
          connect();
        }, reconnectDelay);
      };
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [userId, setChatSessions]);

  return (
    <SseContext.Provider value={undefined}>
      {children}
    </SseContext.Provider>
  );
};

export const useSse = () => {
  useContext(SseContext);
};