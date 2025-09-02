import 'reflect-metadata';
import { Container } from 'inversify';
import { TYPES } from './types';
import { 
  ILogger, 
  IEventBus, 
  IHttpClient,
  ITaskService,
  IStreamService,
  IResearchService 
} from '../interfaces';
import { Logger } from '../implementations/Logger';
import { EventBus } from '../implementations/EventBus';
import { HttpClient } from '../implementations/HttpClient';

const container = new Container({
  defaultScope: 'Singleton',
  autoBindInjectable: true,
});

// Bind core services
container.bind<ILogger>(TYPES.Logger).to(Logger);
container.bind<IEventBus>(TYPES.EventBus).to(EventBus);
container.bind<IHttpClient>(TYPES.HttpClient).to(HttpClient);

// TODO: Bind other services as they are implemented
// container.bind<ITaskService>(TYPES.TaskService).to(TaskService);
// container.bind<IStreamService>(TYPES.StreamService).to(StreamService);
// container.bind<IResearchService>(TYPES.ResearchService).to(ResearchService);

export { container };