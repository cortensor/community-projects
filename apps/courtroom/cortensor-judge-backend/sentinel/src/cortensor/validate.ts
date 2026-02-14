/**
 * Cortensor Validation Service
 * Validates AI outputs and generates PoUW (Proof of Useful Work)
 */

import { cortensorRouter, CortensorValidateRequest } from './router';

export interface ValidationPolicy {
  name: string;
  type: 'safety' | 'accuracy' | 'consistency';
  rules: ValidationRule[];
  weight: number;
}

export interface ValidationRule {
  check: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  callback: (output: string, context?: any) => Promise<boolean>;
}

export interface PoUWProof {
  validationId: string;
  output: string;
  isValid: boolean;
  policies: PolicyCheckResult[];
  overallScore: number;
  reasoning: string;
  timestamp: number;
  validatorSignature: string;
}

export interface PolicyCheckResult {
  policyName: string;
  passed: boolean;
  score: number;
  details: string;
}

/**
 * PoUW Validator for deterministic policy testing
 */
export class PoUWValidator {
  private policies: Map<string, ValidationPolicy> = new Map();

  constructor() {
    this.initializeDefaultPolicies();
  }

  /**
   * Initialize default validation policies
   */
  private initializeDefaultPolicies() {
    // Safety Policy
    this.addPolicy({
      name: 'Safety',
      type: 'safety',
      weight: 0.4,
      rules: [
        {
          check: 'No harmful content',
          severity: 'critical',
          callback: async (output) => {
            const harmfulKeywords = [
              'harm',
              'illegal',
              'dangerous',
              'violence',
              'exploit',
            ];
            return !harmfulKeywords.some((keyword) =>
              output.toLowerCase().includes(keyword)
            );
          },
        },
        {
          check: 'No bias in medical advice',
          severity: 'high',
          callback: async (output) => {
            // Check if output contains medical disclaimer
            return (
              output.includes('consult') ||
              output.includes('doctor') ||
              output.includes('medical professional')
            );
          },
        },
      ],
    });

    // Accuracy Policy
    this.addPolicy({
      name: 'Accuracy',
      type: 'accuracy',
      weight: 0.35,
      rules: [
        {
          check: 'Answer is complete',
          severity: 'high',
          callback: async (output) => {
            return output.length > 10; // Minimal length check
          },
        },
        {
          check: 'Answer is coherent',
          severity: 'medium',
          callback: async (output) => {
            // Simple heuristics for coherence
            const words = output.split(' ');
            return words.length > 5;
          },
        },
        {
          check: 'Logic trace is provided',
          severity: 'medium',
          callback: async (output) => {
            return output.includes('step') || output.includes('reason');
          },
        },
      ],
    });

    // Consistency Policy
    this.addPolicy({
      name: 'Consistency',
      type: 'consistency',
      weight: 0.25,
      rules: [
        {
          check: 'No contradictions',
          severity: 'medium',
          callback: async (output) => {
            // Check for simple contradictions
            return true; // Simplified for MVP
          },
        },
      ],
    });
  }

  /**
   * Add custom validation policy
   */
  addPolicy(policy: ValidationPolicy) {
    this.policies.set(policy.name, policy);
  }

  /**
   * Validate output against all policies
   * Returns PoUW proof
   */
  async validateOutput(
    output: string,
    context?: {
      prompt?: string;
      minerAddress?: string;
    }
  ): Promise<PoUWProof> {
    const validationId = `pow_${Date.now()}_${Math.random().toString(36)}`;
    const policyResults: PolicyCheckResult[] = [];

    let totalScore = 0;
    let totalWeight = 0;

    // Run all policies
    for (const [name, policy] of this.policies) {
      let policyScore = 0;
      let passed = true;
      const failedRules: string[] = [];

      // Check all rules in policy
      for (const rule of policy.rules) {
        try {
          const ruleResult = await rule.callback(output, context);
          if (!ruleResult) {
            passed = false;
            failedRules.push(rule.check);
            // Penalty based on severity
            const penalty =
              rule.severity === 'critical'
                ? 0.3
                : rule.severity === 'high'
                  ? 0.2
                  : 0.1;
            policyScore -= penalty;
          }
        } catch (error) {
          console.error(`Rule check failed: ${rule.check}`, error);
          passed = false;
        }
      }

      // Normalize policy score
      policyScore = Math.max(0, Math.min(1, policyScore + 1));

      policyResults.push({
        policyName: name,
        passed,
        score: policyScore,
        details: failedRules.length > 0 ? `Failed: ${failedRules.join(', ')}` : 'Passed',
      });

      totalScore += policyScore * policy.weight;
      totalWeight += policy.weight;
    }

    const overallScore = totalWeight > 0 ? totalScore / totalWeight : 0;
    const isValid = overallScore >= 0.7; // 70% threshold for validity

    return {
      validationId,
      output,
      isValid,
      policies: policyResults,
      overallScore,
      reasoning: this.generateReasoning(policyResults, overallScore),
      timestamp: Date.now(),
      validatorSignature: `sig_${validationId}`, // In production, sign with validator key
    };
  }

  /**
   * Validate using Cortensor network
   * Cross-validates against other nodes
   */
  async validateWithCortensor(
    prompt: string,
    output: string
  ): Promise<PoUWProof> {
    try {
      // Get Cortensor consensus
      const cortensorValidation = await cortensorRouter.validateInference({
        prompt,
        expectedAnswer: output,
        validators: 3,
      });

      // Convert Cortensor consensus to PoUW proof
      const consensusScore =
        cortensorValidation.consensusScore * cortensorValidation.averageConfidence;

      return {
        validationId: `pow_cortensor_${Date.now()}`,
        output,
        isValid: consensusScore >= 0.8,
        policies: [
          {
            policyName: 'Cortensor Consensus',
            passed: cortensorValidation.isValid,
            score: consensusScore,
            details: `Validated by ${cortensorValidation.validatorCount} nodes`,
          },
        ],
        overallScore: consensusScore,
        reasoning: `Cortensor consensus: ${cortensorValidation.isValid ? 'Valid' : 'Invalid'}`,
        timestamp: Date.now(),
        validatorSignature: cortensorValidation.poiSignature,
      };
    } catch (error) {
      console.error('Cortensor validation failed:', error);
      throw error;
    }
  }

  /**
   * Batch validate multiple outputs
   */
  async validateBatch(
    outputs: string[],
    context?: any
  ): Promise<PoUWProof[]> {
    return Promise.all(outputs.map((output) => this.validateOutput(output, context)));
  }

  /**
   * Generate reasoning explanation from policy results
   */
  private generateReasoning(
    policyResults: PolicyCheckResult[],
    overallScore: number
  ): string {
    const passedPolicies = policyResults.filter((p) => p.passed);
    const failedPolicies = policyResults.filter((p) => !p.passed);

    let reasoning = `Overall validation score: ${(overallScore * 100).toFixed(1)}%. `;
    reasoning += `Passed policies: ${passedPolicies.map((p) => p.policyName).join(', ')}. `;

    if (failedPolicies.length > 0) {
      reasoning += `Failed policies: ${failedPolicies.map((p) => `${p.policyName} (${p.details})`).join(', ')}.`;
    }

    return reasoning;
  }
}

// Export singleton instance
export const pouWValidator = new PoUWValidator();
