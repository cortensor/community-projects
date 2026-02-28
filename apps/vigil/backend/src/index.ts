import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { createServer } from 'http';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { mkdirSync } from 'fs';
import routes, { createWebSocketServer } from './api/routes.js';
import { metricsMonitor } from './monitors/metrics.js';
import { incidentManager } from './managers/incident.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Ensure data directory exists
const dataDir = join(__dirname, '../data');
try {
  mkdirSync(dataDir, { recursive: true });
} catch (err) {
  // Directory already exists
}

const app = express();
const server = createServer(app);
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api', routes);

// WebSocket
createWebSocketServer(server);

// Background monitoring loop
let monitoringInterval: NodeJS.Timeout;

function startMonitoring() {
  console.log('Starting background monitoring...');
  
  monitoringInterval = setInterval(async () => {
    const metrics = metricsMonitor.getCurrentMetrics();
    await incidentManager.processMetrics(metrics);
  }, 10000); // Check every 10 seconds
}

function stopMonitoring() {
  if (monitoringInterval) {
    clearInterval(monitoringInterval);
    console.log('Stopped background monitoring');
  }
}

// Start server
server.listen(PORT, () => {
  console.log(`🚀 Vigil Backend running on port ${PORT}`);
  console.log(`📊 API: http://localhost:${PORT}/api`);
  console.log(`🔌 WebSocket: ws://localhost:${PORT}/ws`);
  
  startMonitoring();
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down gracefully...');
  stopMonitoring();
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGTERM', () => {
  console.log('\nShutting down gracefully...');
  stopMonitoring();
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});
