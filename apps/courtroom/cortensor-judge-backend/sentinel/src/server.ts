/**
 * Express Server Setup
 * REST API for Sentinel Bot operations
 */

import express, { Express, Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { config } from './config/env';
import { EvidenceBundle, DisputeStatus, VerdictType } from './types/evidence';
import { challengeService } from './services/challenge.service';
import { verdictService } from './services/verdict.service';
import { justiceClient } from './web3/justice.client';
import { cortensorRouter } from './cortensor/router';
import { MockEvidenceGenerator } from './evidence/bundle';
import { disputeQueueService } from './queue/dispute.queue';

export class SentinelServer {
  private app: Express;

  constructor() {
    this.app = express();
    this.setupMiddleware();
    this.setupRoutes();
  }

  private setupMiddleware() {
    // Body parsing
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ limit: '10mb', extended: true }));

    // CORS
    this.app.use(cors({
      origin: config.CORS_ORIGIN === '*' ? true : config.CORS_ORIGIN.split(','),
      credentials: true,
    }));

    // Logging middleware
    this.app.use((req: Request, res: Response, next: NextFunction) => {
      const start = Date.now();
      res.on('finish', () => {
        const duration = Date.now() - start;
        console.log(`${req.method} ${req.path} - ${res.statusCode} (${duration}ms)`);
      });
      next();
    });

    // Error handling
    this.app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
      console.error('Unhandled error:', err);
      res.status(500).json({
        success: false,
        error: err.message,
      });
    });
  }

  private setupRoutes() {
    // Health check
    this.app.get('/health', (req: Request, res: Response) => {
      res.json({ status: 'ok', timestamp: Date.now() });
    });

    // ==================== Challenge Routes ====================

    /**
     * POST /challenge
     * Initiate a challenge against suspicious output
     */
    this.app.post('/challenge', async (req: Request, res: Response): Promise<void> => {
      try {
        const { evidence, bondAmount } = req.body;

        if (!evidence || !bondAmount) {
          res.status(400).json({
            success: false,
            error: 'Missing evidence or bondAmount',
          });
          return;
        }

        const result = await challengeService.initiateChallenge(
          evidence as EvidenceBundle,
          bondAmount
        );

        res.json(result);
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    /**
     * POST /monitor
     * Monitor for suspicious outputs
     */
    this.app.post('/monitor', async (req: Request, res: Response): Promise<void> => {
      try {
        const { prompt, threshold } = req.body;

        if (!prompt) {
          res.status(400).json({
            success: false,
            error: 'Missing prompt',
          });
          return;
        }

        const result = await challengeService.monitorForSuspiciousOutputs(
          prompt,
          threshold || config.MIN_SIMILARITY_THRESHOLD
        );

        res.json(result);
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    /**
     * POST /auto-challenge
     * Automatically challenge if suspicious
     */
    this.app.post('/auto-challenge', async (req: Request, res: Response): Promise<void> => {
      try {
        const { evidence, minBond, maxBond } = req.body;

        if (!evidence) {
          res.status(400).json({
            success: false,
            error: 'Missing evidence',
          });
          return;
        }

        const result = await challengeService.autoChallengeIfSuspicious(
          evidence as EvidenceBundle,
          minBond || config.MIN_BOND_AMOUNT,
          maxBond || config.MAX_BOND_AMOUNT
        );

        res.json(result);
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    // ==================== Verdict Routes ====================

    /**
     * POST /verdict/generate
     * Generate verdict for disputed output
     */
    this.app.post('/verdict/generate', async (req: Request, res: Response): Promise<void> => {
      try {
        const { disputeId, evidence, minerOutput } = req.body;

        if (!disputeId || !evidence || !minerOutput) {
          res.status(400).json({
            success: false,
            error: 'Missing required fields',
          });
          return;
        }

        const result = await verdictService.generateVerdict(
          disputeId,
          evidence as EvidenceBundle,
          minerOutput
        );

        res.json(result);
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    /**
     * POST /verdict/submit
     * Submit verdict to Justice contract
     */
    this.app.post('/verdict/submit', async (req: Request, res: Response): Promise<void> => {
      try {
        const { disputeId, evidence, verdict, reasoning } = req.body;

        if (!disputeId || !evidence || !verdict || !reasoning) {
          res.status(400).json({
            success: false,
            error: 'Missing required fields',
          });
          return;
        }

        const result = await verdictService.submitVerdict(
          disputeId,
          evidence as EvidenceBundle,
          verdict as VerdictType,
          reasoning
        );

        res.json(result);
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    /**
     * POST /verdict/execute
     * Execute full verdict workflow
     */
    this.app.post('/verdict/execute', async (req: Request, res: Response): Promise<void> => {
      try {
        const { disputeId, evidence } = req.body;

        if (!disputeId || !evidence) {
          res.status(400).json({
            success: false,
            error: 'Missing disputeId or evidence',
          });
          return;
        }

        const result = await verdictService.executeFullVerdictWorkflow(
          disputeId,
          evidence as EvidenceBundle
        );

        res.json(result);
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    /**
     * POST /dispute/settle
     * Settle a dispute
     */
    this.app.post('/dispute/settle', async (req: Request, res: Response): Promise<void> => {
      try {
        const { disputeId } = req.body;

        if (!disputeId) {
          res.status(400).json({
            success: false,
            error: 'Missing disputeId',
          });
          return;
        }

        const result = await verdictService.settleDispute(disputeId);

        res.json(result);
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    // ==================== Query Routes ====================

    /**
     * GET /dispute/:disputeId
     * Get dispute details
     */
    this.app.get('/dispute/:disputeId', async (req: Request, res: Response) => {
      try {
        const { disputeId } = req.params;
        const dispute = await justiceClient.getDispute(disputeId);
        res.json(dispute);
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    /**
     * GET /miner/:minerAddress/trust-score
     * Get miner trust score
     */
    this.app.get('/miner/:minerAddress/trust-score', async (req: Request, res: Response) => {
      try {
        const { minerAddress } = req.params;
        const score = await justiceClient.getMinerTrustScore(minerAddress);

        res.json({
          minerAddress,
          trustScore: score,
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    /**
     * GET /queue/stats
     * Get queue statistics
     */
    this.app.get('/queue/stats', async (req: Request, res: Response) => {
      try {
        const stats = await disputeQueueService.getQueueStats();
        res.json(stats);
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    // ==================== Mock/Test Routes ====================

    /**
     * POST /test/generate-evidence
     * Generate mock evidence for testing
     */
    this.app.post('/test/generate-evidence', (req: Request, res: Response): void => {
      try {
        const { prompt, minerAddress } = req.body;

        if (!prompt) {
          res.status(400).json({
            success: false,
            error: 'Missing prompt',
          });
          return;
        }

        const evidence = MockEvidenceGenerator.generate(prompt, minerAddress);

        res.json({
          success: true,
          evidence,
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    /**
     * GET /test/health-cortensor
     * Check Cortensor network health
     */
    this.app.get('/test/health-cortensor', async (req: Request, res: Response) => {
      try {
        const isHealthy = await cortensorRouter.healthCheck();

        res.json({
          cortensorHealthy: isHealthy,
          timestamp: Date.now(),
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    });

    // 404 handler
    this.app.use((req: Request, res: Response) => {
      res.status(404).json({
        success: false,
        error: 'Not found',
      });
    });
  }

  public listen(port: number = config.PORT): Promise<void> {
    return new Promise((resolve) => {
      this.app.listen(port, () => {
        console.log(`🚀 Sentinel Server running on port ${port}`);
        resolve();
      });
    });
  }

  public getApp(): Express {
    return this.app;
  }
}
