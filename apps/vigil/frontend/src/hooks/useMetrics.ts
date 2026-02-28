import { useState, useEffect } from 'react';

const WS_URL = 'ws://localhost:3001/ws';

export function useMetrics() {
  const [metrics, setMetrics] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let ws: WebSocket;

    const connect = () => {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setIsConnected(true);
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'metrics') {
          setMetrics(data.data);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected, reconnecting...');
        setTimeout(connect, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    };

    connect();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  return { metrics, isConnected };
}
