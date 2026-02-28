import express from 'express';
import cors from 'cors';
import { WebSocketServer } from 'ws';
import { metricsMonitor } from '../monitors/metrics.js';
import { incidentManager } from '../managers/incident.js';
import { simulator } from '../simulator/index.js';

const router = express.Router();

// Get current metrics
router.get('/metrics/current', (req, res) => {
  const metrics = metricsMonitor.getCurrentMetrics();
  res.json(metrics);
});

// Get metrics history
router.get('/metrics/history', (req, res) => {
  const limit = parseInt(req.query.limit as string) || 100;
  const history = metricsMonitor.getMetricsHistory(limit);
  res.json(history);
});

// Get all incidents
router.get('/incidents', (req, res) => {
  const limit = parseInt(req.query.limit as string) || 50;
  const incidents = incidentManager.getAllIncidents(limit);
  res.json(incidents);
});

// Get active incidents
router.get('/incidents/active', (req, res) => {
  const incidents = incidentManager.getActiveIncidents();
  res.json(incidents);
});

// Get specific incident
router.get('/incidents/:id', (req, res) => {
  const incident = incidentManager.getIncident(req.params.id);
  if (!incident) {
    return res.status(404).json({ error: 'Incident not found' });
  }
  res.json(incident);
});

// Simulate incident (demo mode)
router.post('/simulate', async (req, res) => {
  const { type } = req.body;
  
  if (!['high_latency', 'high_error_rate', 'validator_score_drop'].includes(type)) {
    return res.status(400).json({ error: 'Invalid incident type' });
  }

  const metrics = simulator.simulateIncident(type);
  const incident = await incidentManager.processMetrics(metrics);
  
  res.json({ success: true, incident });
});

// Health check
router.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: Date.now() });
});

export function createWebSocketServer(server: any) {
  const wss = new WebSocketServer({ server, path: '/ws' });

  wss.on('connection', (ws) => {
    console.log('WebSocket client connected');

    // Send metrics every 2 seconds
    const interval = setInterval(() => {
      if (ws.readyState === ws.OPEN) {
        const metrics = metricsMonitor.getCurrentMetrics();
        ws.send(JSON.stringify({ type: 'metrics', data: metrics }));
      }
    }, 2000);

    ws.on('close', () => {
      clearInterval(interval);
      console.log('WebSocket client disconnected');
    });
  });

  return wss;
}

export default router;
