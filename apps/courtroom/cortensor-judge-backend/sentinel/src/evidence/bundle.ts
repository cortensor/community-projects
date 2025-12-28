/**
 * Evidence Bundle Management
 * Creates and manages evidence bundles for the Justice contract
 */

import crypto from 'crypto';
import { EvidenceBundle, LogicTrace } from '../types/evidence';

export interface BundleMetadata {
  bundleId: string;
  createdAt: number;
  size: number;
  hash: string;
}

/**
 * Evidence Bundle Service
 */
export class EvidenceBundleService {
  /**
   * Create evidence bundle from inference data
   */
  static createBundle(
    prompt: string,
    minerResult: string,
    logicTrace: LogicTrace[],
    poiHash: string,
    miner: string,
    modelId: number,
    modelName: string,
    ipfsHash: string
  ): EvidenceBundle {
    // Create promptHash from original prompt
    const promptHash = crypto
      .createHash('sha256')
      .update(prompt)
      .digest('hex');

    // Create signature (in production, miner would sign)
    const signature = crypto
      .createHash('sha256')
      .update(`${minerResult}${poiHash}${miner}`)
      .digest('hex');

    return {
      promptHash,
      minerResult,
      logicTrace,
      poiHash,
      ipfsHash,
      modelId,
      modelName,
      miner,
      timestamp: Math.floor(Date.now() / 1000),
      signature,
    };
  }

  /**
   * Generate bundle metadata
   */
  static generateMetadata(bundle: EvidenceBundle): BundleMetadata {
    const bundleJson = JSON.stringify(bundle);
    const hash = crypto
      .createHash('sha256')
      .update(bundleJson)
      .digest('hex');

    return {
      bundleId: `bundle_${hash.slice(0, 16)}`,
      createdAt: bundle.timestamp,
      size: bundleJson.length,
      hash,
    };
  }

  /**
   * Validate bundle integrity
   */
  static validateBundle(bundle: EvidenceBundle): {
    isValid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    if (!bundle.promptHash) errors.push('Missing promptHash');
    if (!bundle.minerResult) errors.push('Missing minerResult');
    if (!bundle.logicTrace || bundle.logicTrace.length === 0)
      errors.push('Missing logicTrace');
    if (!bundle.poiHash) errors.push('Missing poiHash');
    if (!bundle.ipfsHash) errors.push('Missing ipfsHash');
    if (!bundle.miner || !bundle.miner.startsWith('0x'))
      errors.push('Invalid miner address');
    if (!bundle.signature) errors.push('Missing signature');

    return {
      isValid: errors.length === 0,
      errors,
    };
  }

  /**
   * Extract comparable output from bundle
   * Used for similarity comparisons
   */
  static extractComparableOutput(bundle: EvidenceBundle): string {
    // Normalize output for comparison
    return bundle.minerResult
      .toLowerCase()
      .trim()
      .replace(/\s+/g, ' ');
  }

  /**
   * Convert bundle to blockchain format
   * Prepares data for Justice contract
   */
  static toBundleForChain(bundle: EvidenceBundle) {
    return {
      promptHash: bundle.promptHash,
      minerResult: bundle.minerResult,
      logicTrace: JSON.stringify(bundle.logicTrace),
      poiHash: bundle.poiHash,
      ipfsHash: bundle.ipfsHash,
      modelId: bundle.modelId,
      miner: bundle.miner,
      timestamp: bundle.timestamp,
    };
  }
}

/**
 * Logic Trace Builder
 * Constructs chain-of-thought reasoning
 */
export class LogicTraceBuilder {
  private steps: LogicTrace[] = [];

  addStep(
    description: string,
    reasoning: string,
    confidence: number = 0.8
  ): this {
    this.steps.push({
      step: this.steps.length + 1,
      description,
      reasoning,
      confidence: Math.min(1, Math.max(0, confidence)),
    });
    return this;
  }

  build(): LogicTrace[] {
    return [...this.steps];
  }

  clear(): this {
    this.steps = [];
    return this;
  }

  getSteps(): LogicTrace[] {
    return this.steps;
  }

  getTotalConfidence(): number {
    if (this.steps.length === 0) return 0;
    const sum = this.steps.reduce((acc, step) => acc + step.confidence, 0);
    return sum / this.steps.length;
  }
}

/**
 * Mock Evidence Generator for testing
 */
export class MockEvidenceGenerator {
  /**
   * Generate realistic mock evidence bundle
   */
  static generate(
    prompt: string,
    minerAddress: string = '0x' + crypto.randomBytes(20).toString('hex')
  ): EvidenceBundle {
    const builder = new LogicTraceBuilder();

    // Generate plausible logic trace
    builder
      .addStep('Parse input', `Analyzing prompt: "${prompt.slice(0, 50)}..."`, 0.95)
      .addStep(
        'Identify intent',
        'Determined user is asking for information',
        0.9
      )
      .addStep(
        'Search knowledge',
        'Querying knowledge base for relevant information',
        0.85
      )
      .addStep(
        'Construct response',
        'Assembling comprehensive answer',
        0.88
      )
      .addStep('Validate output', 'Checking for accuracy and safety', 0.92);

    const mockResult = `Based on the query "${prompt}", here's a comprehensive response with relevant information and context.`;
    const mockIpfsHash = 'Qm' + crypto.randomBytes(32).toString('hex');

    return EvidenceBundleService.createBundle(
      prompt,
      mockResult,
      builder.build(),
      `poi_${crypto.randomBytes(16).toString('hex')}`,
      minerAddress,
      1,
      'Llama-3',
      mockIpfsHash
    );
  }
}
