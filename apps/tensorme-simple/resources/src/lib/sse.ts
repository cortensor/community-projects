import { EventEmitter } from 'events';

class SseManager {
  private emitters: Map<string, EventEmitter> = new Map();

  public getEmitter(userId: string): EventEmitter {
    if (!this.emitters.has(userId)) {
      this.emitters.set(userId, new EventEmitter());
    }
    return this.emitters.get(userId)!;
  }

  public removeEmitter(userId: string) {
    const emitter = this.emitters.get(userId);
    if (emitter) {
      emitter.removeAllListeners();
      this.emitters.delete(userId);
    }
  }
}

export const sseManager = new SseManager();