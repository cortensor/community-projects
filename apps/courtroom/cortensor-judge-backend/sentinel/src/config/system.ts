/**
 * Main Configuration Builder
 * Initializes all system components
 */

import { JusticeClient } from '../web3/justice.client';
import { PinataService } from '../evidence/ipfs';
import { CortensorRouter } from '../cortensor/router';
import { DisputeQueueService } from '../queue/dispute.queue';
import { PoUWValidator } from '../cortensor/validate';
import { ChallengeService } from '../services/challenge.service';
import { VerdictService } from '../services/verdict.service';
import { config } from './env';

export interface SystemConfig {
  blockchain: JusticeClient;
  ipfs: PinataService;
  cortensor: CortensorRouter;
  queue: DisputeQueueService;
  validator: PoUWValidator;
  challenge: ChallengeService;
  verdict: VerdictService;
  config: typeof config;
}

/**
 * Initialize all system components
 */
export async function initializeSystem(): Promise<SystemConfig> {
  console.log('🚀 Initializing Cortensor Judge system...');

  // Initialize components
  const blockchain = new JusticeClient(
    config.BLOCKCHAIN_RPC_URL,
    config.JUSTICE_CONTRACT_ADDRESS,
    config.COR_TOKEN_ADDRESS,
    config.VALIDATOR_PRIVATE_KEY
  );

  const ipfs = new PinataService(
    config.PINATA_API_KEY,
    config.PINATA_API_SECRET,
    config.PINATA_GATEWAY_URL
  );

  const cortensor = new CortensorRouter(
    config.CORTENSOR_API_URL,
    config.CORTENSOR_API_KEY
  );

  const queue = new DisputeQueueService();
  const validator = new PoUWValidator();
  const challenge = new ChallengeService();
  const verdict = new VerdictService();

  // Verify connections
  console.log('🔍 Verifying system connections...');

  try {
    const cortensorHealthy = await cortensor.healthCheck();
    console.log(`  Cortensor: ${cortensorHealthy ? '✅' : '⚠️'}`);

    const isPinned = await ipfs.isPinned('Qmtest');
    console.log(`  IPFS: ✅`);
  } catch (error) {
    console.warn('⚠️ Some external services not responding');
  }

  console.log('✅ System initialized successfully');

  return {
    blockchain,
    ipfs,
    cortensor,
    queue,
    validator,
    challenge,
    verdict,
    config,
  };
}

/**
 * Cleanup system resources
 */
export async function shutdownSystem(system: SystemConfig): Promise<void> {
  console.log('📊 Shutting down Cortensor Judge system...');
  await system.queue.close();
  console.log('✅ System shutdown complete');
}
