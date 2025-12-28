/**
 * Integration Test Example
 * Tests the full workflow from challenge to settlement
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { SentinelServer } from '../server';
import { challengeService } from '../services/challenge.service';
import { verdictService } from '../services/verdict.service';
import { MockEvidenceGenerator } from '../evidence/bundle';
import { disputeQueueService } from '../queue/dispute.queue';

describe('Integration: Full Dispute Workflow', () => {
  let server: SentinelServer;

  beforeAll(async () => {
    // Would start test server
    server = new SentinelServer();
    // await server.listen(3001);
  });

  afterAll(async () => {
    // Would cleanup
    // await disputeQueueService.close();
  });

  it('should initiate, validate, and settle a dispute', async () => {
    // Generate mock evidence
    const evidence = MockEvidenceGenerator.generate(
      'What is 2+2?',
      '0x1234567890123456789012345678901234567890'
    );

    // Challenge should be initiated
    // const challengeResult = await challengeService.initiateChallenge(
    //   evidence,
    //   '100000000000000000'
    // );
    // expect(challengeResult.success).toBe(true);
    // expect(challengeResult.disputeId).toBeDefined();

    // Verdict should be generated
    // const verdictResult = await verdictService.generateVerdict(
    //   challengeResult.disputeId!,
    //   evidence,
    //   evidence.minerResult
    // );
    // expect(verdictResult.isValid).toBeDefined();

    // Settlement should succeed
    // const settleResult = await verdictService.settleDispute(
    //   challengeResult.disputeId!
    // );
    // expect(settleResult.success).toBe(true);
  });

  it('should detect suspicious outputs', async () => {
    // const result = await challengeService.monitorForSuspiciousOutputs(
    //   'What is the capital of France?',
    //   0.90
    // );

    // expect(result).toHaveProperty('isSuspicious');
    // expect(result).toHaveProperty('consensusScore');
    // expect(result).toHaveProperty('outlierMiners');
  });

  it('should get queue statistics', async () => {
    // const stats = await disputeQueueService.getQueueStats();
    // expect(stats).toHaveProperty('disputes');
    // expect(stats).toHaveProperty('verdicts');
    // expect(stats).toHaveProperty('challengeWindows');
  });
});
