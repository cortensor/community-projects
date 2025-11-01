import { injectable } from 'inversify';
import { IEventBus, Unsubscribe } from '../interfaces';

type EventCallback = (data?: any) => void;

@injectable()
export class EventBus implements IEventBus {
  private listeners: Map<string, Set<EventCallback>> = new Map();

  emit(event: string, data?: any): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event callback for ${event}:`, error);
        }
      });
    }
  }

  on(event: string, callback: EventCallback): Unsubscribe {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    
    this.listeners.get(event)!.add(callback);

    return () => {
      this.off(event, callback);
    };
  }

  off(event: string, callback: EventCallback): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        this.listeners.delete(event);
      }
    }
  }

  once(event: string, callback: EventCallback): Unsubscribe {
    const onceCallback = (data?: any) => {
      callback(data);
      this.off(event, onceCallback);
    };

    return this.on(event, onceCallback);
  }
}