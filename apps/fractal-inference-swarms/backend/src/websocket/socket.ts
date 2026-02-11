import WebSocket, { WebSocketServer } from 'ws';
import { Server as HttpServer } from 'http';
import { eventBus, SwarmEventPayload } from '../utils/EventBus';
import { config } from '../config';
import { createChildLogger } from '../utils/logger';

const logger = createChildLogger('WebSocket');

interface TrackedClient {
  ws: WebSocket;
  id: string;
  subscribedTasks: Set<string>;
  connectedAt: number;
  lastPing: number;
  isAlive: boolean;
}

export class SwarmWebSocketServer {
  private wss: WebSocketServer | null = null;
  private clients: Map<string, TrackedClient> = new Map();
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private clientIdCounter: number = 0;

  initialize(server: HttpServer): void {
    this.wss = new WebSocketServer({ server, path: '/ws' });

    this.wss.on('connection', (ws: WebSocket) => {
      const clientId = `client-${++this.clientIdCounter}-${Date.now()}`;
      const client: TrackedClient = {
        ws,
        id: clientId,
        subscribedTasks: new Set(),
        connectedAt: Date.now(),
        lastPing: Date.now(),
        isAlive: true,
      };

      this.clients.set(clientId, client);
      logger.info('Client connected', { clientId, totalClients: this.clients.size });

      this.sendToClient(client, {
        type: 'connection',
        clientId,
        timestamp: Date.now(),
        message: 'Connected to Fractal Inference Swarms WebSocket',
      });

      ws.on('message', (data: Buffer) => {
        try {
          const message = JSON.parse(data.toString());
          this.handleClientMessage(client, message);
        } catch {
          this.sendToClient(client, {
            type: 'error',
            message: 'Invalid JSON message',
          });
        }
      });

      ws.on('pong', () => {
        client.isAlive = true;
        client.lastPing = Date.now();
      });

      ws.on('close', () => {
        this.clients.delete(clientId);
        logger.info('Client disconnected', { clientId, totalClients: this.clients.size });
      });

      ws.on('error', (error) => {
        logger.error('WebSocket client error', { clientId, error: error.message });
        this.clients.delete(clientId);
      });
    });

    this.setupEventForwarding();
    this.startHeartbeat();

    logger.info('WebSocket server initialized');
  }

  private handleClientMessage(client: TrackedClient, message: Record<string, unknown>): void {
    switch (message.type) {
      case 'subscribe':
        if (typeof message.taskId === 'string') {
          client.subscribedTasks.add(message.taskId);
          this.sendToClient(client, {
            type: 'subscribed',
            taskId: message.taskId,
          });
          logger.debug('Client subscribed to task', {
            clientId: client.id,
            taskId: message.taskId,
          });
        }
        break;

      case 'unsubscribe':
        if (typeof message.taskId === 'string') {
          client.subscribedTasks.delete(message.taskId);
          this.sendToClient(client, {
            type: 'unsubscribed',
            taskId: message.taskId,
          });
        }
        break;

      case 'subscribe_all':
        client.subscribedTasks.add('*');
        this.sendToClient(client, { type: 'subscribed', taskId: '*' });
        break;

      case 'ping':
        this.sendToClient(client, { type: 'pong', timestamp: Date.now() });
        break;

      default:
        this.sendToClient(client, {
          type: 'error',
          message: `Unknown message type: ${message.type}`,
        });
    }
  }

  private setupEventForwarding(): void {
    eventBus.onSwarmEvent('*', (payload: SwarmEventPayload) => {
      const message = {
        type: 'swarm_event',
        event: payload.event,
        taskId: payload.taskId,
        data: payload.data,
        timestamp: payload.timestamp,
      };

      for (const client of this.clients.values()) {
        if (
          client.subscribedTasks.has('*') ||
          client.subscribedTasks.has(payload.taskId)
        ) {
          this.sendToClient(client, message);
        }
      }
    });
  }

  private sendToClient(client: TrackedClient, data: unknown): void {
    if (client.ws.readyState === WebSocket.OPEN) {
      try {
        client.ws.send(JSON.stringify(data));
      } catch (error) {
        logger.error('Failed to send to client', {
          clientId: client.id,
          error: (error as Error).message,
        });
      }
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      for (const [id, client] of this.clients) {
        if (!client.isAlive) {
          logger.debug('Terminating unresponsive client', { clientId: id });
          client.ws.terminate();
          this.clients.delete(id);
          continue;
        }
        client.isAlive = false;
        client.ws.ping();
      }
    }, config.websocket.heartbeatInterval);
  }

  broadcast(data: unknown): void {
    const message = JSON.stringify(data);
    for (const client of this.clients.values()) {
      if (client.ws.readyState === WebSocket.OPEN) {
        client.ws.send(message);
      }
    }
  }

  getConnectionCount(): number {
    return this.clients.size;
  }

  shutdown(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
    for (const client of this.clients.values()) {
      client.ws.close(1001, 'Server shutting down');
    }
    this.clients.clear();
    this.wss?.close();
    logger.info('WebSocket server shut down');
  }
}

export const wsServer = new SwarmWebSocketServer();