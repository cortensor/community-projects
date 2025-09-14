import { StreamEvent } from '@/types/research';

/**
 * Manages streaming of research events to clients
 */
export class StreamManager {
  private streams: Map<string, ReadableStreamDefaultController> = new Map();
  private eventQueues: Map<string, StreamEvent[]> = new Map();
  private activeConnections: Map<string, number> = new Map();

  /**
   * Create a new stream for a session
   */
  public createStream(sessionId: string): ReadableStream {
    return new ReadableStream({
      start: (controller) => {
        this.streams.set(sessionId, controller);
        this.activeConnections.set(sessionId, (this.activeConnections.get(sessionId) || 0) + 1);
        
        // Send any queued events
        const queue = this.eventQueues.get(sessionId);
        if (queue) {
          queue.forEach(event => this.sendEvent(controller, event));
          this.eventQueues.delete(sessionId);
        }
        
        // Send initial connection event
        this.sendEvent(controller, {
          type: 'connection',
          data: { status: 'connected', sessionId }
        });
      },
      cancel: () => {
        this.handleStreamClose(sessionId);
      }
    });
  }

  /**
   * Send an event to a stream
   */
  public sendToStream(sessionId: string, event: StreamEvent): void {
    const controller = this.streams.get(sessionId);
    
    if (controller) {
      this.sendEvent(controller, event);
    } else {
      // Queue event if stream not yet connected
      if (!this.eventQueues.has(sessionId)) {
        this.eventQueues.set(sessionId, []);
      }
      this.eventQueues.get(sessionId)!.push(event);
    }
  }

  /**
   * Send event to controller
   */
  private sendEvent(controller: ReadableStreamDefaultController, event: any): void {
    try {
      const data = `data: ${JSON.stringify(event)}\n\n`;
      controller.enqueue(new TextEncoder().encode(data));
    } catch (error) {
      console.error('Failed to send event:', error);
    }
  }

  /**
   * Handle stream close
   */
  private handleStreamClose(sessionId: string): void {
    const connections = this.activeConnections.get(sessionId) || 1;
    
    if (connections <= 1) {
      this.streams.delete(sessionId);
      this.activeConnections.delete(sessionId);
      this.eventQueues.delete(sessionId);
    } else {
      this.activeConnections.set(sessionId, connections - 1);
    }
  }

  /**
   * Close a stream
   */
  public closeStream(sessionId: string): void {
    const controller = this.streams.get(sessionId);
    
    if (controller) {
      try {
        this.sendEvent(controller, {
          type: 'connection',
          data: { status: 'closing', sessionId }
        });
        controller.close();
      } catch (error) {
        console.error('Error closing stream:', error);
      }
      
      this.streams.delete(sessionId);
      this.activeConnections.delete(sessionId);
      this.eventQueues.delete(sessionId);
    }
  }

  /**
   * Check if a stream is active
   */
  public isStreamActive(sessionId: string): boolean {
    return this.streams.has(sessionId);
  }

  /**
   * Get active connection count
   */
  public getConnectionCount(sessionId: string): number {
    return this.activeConnections.get(sessionId) || 0;
  }

  /**
   * Broadcast to all active streams
   */
  public broadcast(event: any): void {
    this.streams.forEach((controller, sessionId) => {
      this.sendEvent(controller, event);
    });
  }
}

// Singleton instance
export const streamManager = new StreamManager();