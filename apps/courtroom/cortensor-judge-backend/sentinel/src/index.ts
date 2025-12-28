/**
 * Main Entry Point for Sentinel Service
 * Initializes all components and starts the server
 */

import { SentinelServer } from './server';
import { disputeQueueService } from './queue/dispute.queue';
import { verdictService } from './services/verdict.service';
import { config } from './config/env';

/**
 * Application entry point
 */
async function main() {
  try {
    console.log('🔍 Cortensor Judge - Sentinel Bot initializing...');
    console.log(`Environment: ${config.NODE_ENV}`);
    console.log(`Network: ${config.NETWORK}`);

    // Initialize server
    const server = new SentinelServer();

    // Start queue processors
    console.log('⏳ Starting queue processors...');

    // Dispute queue processor
    await disputeQueueService.startDisputeWorker(async (job) => {
      console.log(`Processing dispute window closure for: ${job.disputeId}`);
      // Window closure logic would be here
    });

    // Verdict queue processor
    await disputeQueueService.startVerdictWorker(async (job) => {
      console.log(`Processing verdict for: ${job.disputeId}`);
      // Verdict processing logic
    });

    // Challenge window monitor
    await disputeQueueService.startChallengeWindowMonitor(async (disputeId) => {
      console.log(`Challenge window closed for dispute: ${disputeId}`);
      // Auto-settle logic could go here
    });

    // Event listeners
    disputeQueueService.onDisputeCompleted((disputeId) => {
      console.log(`✅ Dispute ${disputeId} processed successfully`);
    });

    disputeQueueService.onDisputeFailed((disputeId, error) => {
      console.error(`❌ Dispute ${disputeId} processing failed:`, error);
    });

    // Start Express server
    console.log('🚀 Starting Express server...');
    await server.listen(config.PORT);

    // Setup graceful shutdown
    process.on('SIGINT', async () => {
      console.log('\n📊 Shutting down gracefully...');
      await disputeQueueService.close();
      console.log('✅ Sentinel Bot stopped');
      process.exit(0);
    });

    console.log('✅ Sentinel Bot is running and monitoring the network');
  } catch (error) {
    console.error('❌ Failed to start Sentinel Bot:', error);
    process.exit(1);
  }
}

// Run application
main();
