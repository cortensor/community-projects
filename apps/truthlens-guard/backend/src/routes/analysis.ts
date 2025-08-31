import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { CortensorService } from '../services/cortensorService';
import { AggregationEngine } from '../services/aggregationEngine';
import { DatabaseService } from '../services/database';
import { logger } from '../utils/logger';

const router = Router();
const cortensorService = new CortensorService();
const aggregationEngine = new AggregationEngine();

// Validation schemas
const analyzeRequestSchema = z.object({
  claim: z.string().min(1).max(2000),
  type: z.enum(['text', 'url']),
  options: z.object({
    minMiners: z.number().min(1).max(20).optional().default(3),
    timeout: z.number().min(5000).max(60000).optional().default(30000)
  }).optional().default({})
});

type AnalyzeRequest = z.infer<typeof analyzeRequestSchema>;

// POST /api/analysis/analyze
router.post('/analyze', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const validation = analyzeRequestSchema.safeParse(req.body);
    
    if (!validation.success) {
      return res.status(400).json({
        success: false,
        error: 'Invalid request data',
        details: validation.error.errors
      });
    }

    const { claim, type, options } = validation.data as AnalyzeRequest;

    logger.info('Starting fact-check analysis', {
      claimLength: claim.length,
      type,
      options
    });

    // Step 1: Query Cortensor network
    const minerResponses = await cortensorService.queryMiners({
      claim,
      type,
      minMiners: options.minMiners || 3,
      timeout: options.timeout || 30000
    });

    logger.info('Received miner responses', {
      responseCount: minerResponses.length
    });

    // Step 2: Aggregate results
    const aggregatedResult = aggregationEngine.aggregateResponses(minerResponses);

    // Step 3: Return structured response
    const response = {
      success: true,
      data: {
        claim,
        type,
        analysis: {
          credibilityScore: aggregatedResult.credibilityScore,
          confidence: aggregatedResult.confidence,
          isCredible: aggregatedResult.isCredible,
          consensus: aggregatedResult.consensus,
          supportingSources: aggregatedResult.supportingSources,
          minerResponses: minerResponses.map(r => ({
            minerId: r.minerId,
            score: r.score,
            reasoning: r.reasoning,
            sources: r.sources
          }))
        },
        metadata: {
          processedAt: new Date().toISOString(),
          minerCount: minerResponses.length,
          processingTimeMs: aggregatedResult.processingTimeMs
        }
      }
    };

    logger.info('Analysis completed successfully', {
      credibilityScore: aggregatedResult.credibilityScore,
      minerCount: minerResponses.length
    });

    res.json(response);
  } catch (error) {
    logger.error('Analysis failed', { error });
    next(error);
  }
});

// GET /api/analysis/analytics
router.get('/analytics', (req: Request, res: Response) => {
  res.json({
    success: true,
    data: DatabaseService.getAnalytics()
  });
});

export { router as analysisRouter };
