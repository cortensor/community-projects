import { Router, Request, Response, NextFunction } from 'express';
import { orchestrator } from '../agents/Orchestrator';
import { x402Engine } from '../payments/X402Mock';
import { scoringEngine } from '../engine/ScoringEngine';
import { TaskCreateRequest } from '../models/Task';
import { wsServer } from '../websocket/socket';
import { createChildLogger } from '../utils/logger';

const logger = createChildLogger('API');
const router = Router();

function asyncHandler(fn: (req: Request, res: Response, next: NextFunction) => Promise<void>) {
  return (req: Request, res: Response, next: NextFunction) => {
    fn(req, res, next).catch(next);
  };
}

// Health check
router.get('/health', (_req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    service: 'fractal-inference-swarms',
    timestamp: Date.now(),
    uptime: process.uptime(),
    wsConnections: wsServer.getConnectionCount(),
  });
});

// Submit a new task
router.post(
  '/task',
  asyncHandler(async (req: Request, res: Response) => {
    const { title, description, priority, swarmSize, metadata } = req.body;

    if (!title || !description) {
      res.status(400).json({
        error: 'Validation failed',
        details: 'title and description are required',
      });
      return;
    }

    if (swarmSize && (swarmSize < 2 || swarmSize > 20)) {
      res.status(400).json({
        error: 'Validation failed',
        details: 'swarmSize must be between 2 and 20',
      });
      return;
    }

    const request: TaskCreateRequest = {
      title,
      description,
      priority: priority || 'medium',
      swarmSize: swarmSize || undefined,
      metadata: metadata || {},
    };

    logger.info('New task submission', { title, priority: request.priority, swarmSize: request.swarmSize });
    const task = await orchestrator.submitTask(request);

    res.status(201).json({
      success: true,
      task,
      message: 'Task submitted — swarm pipeline initiated',
    });
  })
);

// Get task by ID
router.get('/task/:id', (req: Request, res: Response) => {
  const task = orchestrator.getTask(req.params.id);
  if (!task) {
    res.status(404).json({ error: 'Task not found' });
    return;
  }

  const session = orchestrator.getSessionForTask(req.params.id);
  res.json({
    task,
    session: session || null,
    scoredResults: orchestrator.getScoredResultsForTask(req.params.id),
  });
});

// Get all tasks
router.get('/tasks', (_req: Request, res: Response) => {
  const tasks = orchestrator.getAllTasks();
  res.json({
    count: tasks.length,
    tasks,
  });
});

// Get agents for a task
router.get('/agents/:taskId', (req: Request, res: Response) => {
  const agents = orchestrator.getAgentsForTask(req.params.taskId);
  const scored = orchestrator.getScoredResultsForTask(req.params.taskId);

  res.json({
    taskId: req.params.taskId,
    agentCount: agents.length,
    agents,
    scoredResults: scored,
  });
});

// Get reward ledger
router.get('/ledger', (_req: Request, res: Response) => {
  const ledger = orchestrator.getLedger();
  const stats = x402Engine.getLedgerStats();

  res.json({
    transactionCount: ledger.length,
    transactions: ledger,
    paymentStats: stats,
    balances: x402Engine.getAllBalances(),
  });
});

// Get payment history for specific agent
router.get('/ledger/agent/:agentId', (req: Request, res: Response) => {
  const ledger = orchestrator.getLedger();
  const agentTransactions = ledger.filter((t) => t.agentId === req.params.agentId);
  const walletAddress = `agent-wallet-${req.params.agentId.slice(0, 12)}`;

  res.json({
    agentId: req.params.agentId,
    transactionCount: agentTransactions.length,
    transactions: agentTransactions,
    balance: x402Engine.getBalance(walletAddress),
    paymentHistory: x402Engine.getPaymentHistory(walletAddress),
  });
});

// Get system metrics
router.get('/metrics', (_req: Request, res: Response) => {
  const metrics = orchestrator.getMetrics();
  const paymentStats = x402Engine.getLedgerStats();

  res.json({
    swarm: metrics,
    payments: paymentStats,
    scoring: scoringEngine.getWeights(),
    system: {
      memoryUsage: process.memoryUsage(),
      uptime: process.uptime(),
      wsConnections: wsServer.getConnectionCount(),
    },
  });
});

// Get all swarm sessions
router.get('/sessions', (_req: Request, res: Response) => {
  const sessions = orchestrator.getAllSessions();
  res.json({
    count: sessions.length,
    sessions,
  });
});

// Get specific session
router.get('/session/:taskId', (req: Request, res: Response) => {
  const session = orchestrator.getSessionForTask(req.params.taskId);
  if (!session) {
    res.status(404).json({ error: 'Session not found' });
    return;
  }
  res.json({ session });
});

// Update scoring weights
router.put('/config/scoring', (req: Request, res: Response) => {
  const { confidence, speed, reliability } = req.body;
  try {
    scoringEngine.updateWeights({ confidence, speed, reliability });
    res.json({
      success: true,
      weights: scoringEngine.getWeights(),
    });
  } catch (error) {
    res.status(400).json({
      error: 'Invalid weights',
      details: (error as Error).message,
    });
  }
});

export { router as apiRouter };