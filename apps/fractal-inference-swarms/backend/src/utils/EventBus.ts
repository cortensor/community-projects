import { EventEmitter } from 'events';

export type SwarmEvent =
  | 'task:created'
  | 'task:splitting'
  | 'task:subtasks_ready'
  | 'task:agents_spawning'
  | 'task:inference_started'
  | 'task:inference_complete'
  | 'task:scoring_started'
  | 'task:scoring_complete'
  | 'task:merging_started'
  | 'task:merge_complete'
  | 'task:validation_complete'
  | 'task:rewards_distributed'
  | 'task:completed'
  | 'task:failed'
  | 'agent:spawned'
  | 'agent:started'
  | 'agent:progress'
  | 'agent:completed'
  | 'agent:failed'
  | 'reward:distributed'
  | 'metrics:updated';

export interface SwarmEventPayload {
  event: SwarmEvent;
  taskId: string;
  data: unknown;
  timestamp: number;
}

class EventBus extends EventEmitter {
  private static instance: EventBus;

  private constructor() {
    super();
    this.setMaxListeners(100);
  }

  static getInstance(): EventBus {
    if (!EventBus.instance) {
      EventBus.instance = new EventBus();
    }
    return EventBus.instance;
  }

  emitSwarmEvent(event: SwarmEvent, taskId: string, data: unknown): void {
    const payload: SwarmEventPayload = {
      event,
      taskId,
      data,
      timestamp: Date.now(),
    };
    this.emit(event, payload);
    this.emit('*', payload);
  }

  onSwarmEvent(event: SwarmEvent | '*', handler: (payload: SwarmEventPayload) => void): void {
    this.on(event, handler);
  }

  offSwarmEvent(event: SwarmEvent | '*', handler: (payload: SwarmEventPayload) => void): void {
    this.off(event, handler);
  }
}

export const eventBus = EventBus.getInstance();