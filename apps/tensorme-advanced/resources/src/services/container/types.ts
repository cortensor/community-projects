export const TYPES = {
  // Services
  TaskService: Symbol.for('TaskService'),
  ResearchService: Symbol.for('ResearchService'),
  QueueService: Symbol.for('QueueService'),
  StreamService: Symbol.for('StreamService'),
  ModelService: Symbol.for('ModelService'),
  SessionService: Symbol.for('SessionService'),
  
  // Repositories
  MessageRepository: Symbol.for('MessageRepository'),
  
  // External
  HttpClient: Symbol.for('HttpClient'),
  Logger: Symbol.for('Logger'),
  EventBus: Symbol.for('EventBus'),
};