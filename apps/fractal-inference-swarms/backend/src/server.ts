import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import http from 'http';
import { config, validateConfig } from './config';
import { apiRouter } from './api/routes';
import { wsServer } from './websocket/socket';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';
import { requestLogger } from './middleware/requestLogger';
import { logger } from './utils/logger';

validateConfig(config);

const app = express();
const server = http.createServer(app);

// Security & parsing
app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({ origin: config.server.corsOrigin, credentials: true }));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Logging
app.use(requestLogger);

// API routes
app.use('/api', apiRouter);

// Error handling
app.use(notFoundHandler);
app.use(errorHandler);

// Initialize WebSocket
wsServer.initialize(server);

// Start server
server.listen(config.server.port, '0.0.0.0', () => {
    logger.info('=== Fractal Inference Swarms Backend ===', {
      port: config.server.port,
      host: '0.0.0.0', // Updated log to reflect reality
      env: config.server.nodeEnv,
      wsPath: '/ws',
      corsOrigin: config.server.corsOrigin,
    });
  logger.info('Orchestrator config', {
    maxAgents: config.orchestrator.maxConcurrentAgents,
    defaultSwarmSize: config.orchestrator.defaultSwarmSize,
    splitStrategy: config.orchestrator.taskSplitStrategy,
  });
  logger.info('Scoring weights', config.scoring);
  logger.info('Reward config', config.reward);
});

// Graceful shutdown
function gracefulShutdown(signal: string): void {
  logger.info(`${signal} received — shutting down gracefully`);
  wsServer.shutdown();
  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 10000);
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('unhandledRejection', (reason) => {
  logger.error('Unhandled promise rejection', { reason });
});
process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception', { error: error.message, stack: error.stack });
  process.exit(1);
});

export { app, server };