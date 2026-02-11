'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { SwarmEvent } from '@/types';

type EventHandler = (event: SwarmEvent) => void;

interface UseWebSocketReturn {
  connected: boolean;
  subscribe: (taskId: string) => void;
  subscribeAll: () => void;
  lastEvent: SwarmEvent | null;
  events: SwarmEvent[];
}

export function useWebSocket(onEvent?: EventHandler): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SwarmEvent | null>(null);
  const [events, setEvents] = useState<SwarmEvent[]>([]);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:3001/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({ type: 'subscribe_all' }));
    };

    ws.onmessage = (msgEvent) => {
      try {
        const data = JSON.parse(msgEvent.data) as SwarmEvent;
        if (data.type === 'swarm_event') {
          setLastEvent(data);
          setEvents((prev) => [data, ...prev].slice(0, 200));
          onEventRef.current?.(data);
        }
      } catch {
        // ignore non-JSON messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback((taskId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', taskId }));
    }
  }, []);

  const subscribeAll = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe_all' }));
    }
  }, []);

  return { connected, subscribe, subscribeAll, lastEvent, events };
}