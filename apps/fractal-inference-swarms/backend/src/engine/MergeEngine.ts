import { ScoredResult } from '../models/AgentResult';
import { MergedOutput, ValidationDetail } from '../models/Task';
import { createChildLogger } from '../utils/logger';

const logger = createChildLogger('MergeEngine');

export type MergeStrategy = 'weighted_consensus' | 'best_pick' | 'hierarchical_merge';

export class MergeEngine {
  mergeResults(
    scoredResults: ScoredResult[],
    taskId: string,
    strategy: MergeStrategy = 'weighted_consensus'
  ): MergedOutput {
    logger.info('Merging agent outputs', {
      taskId,
      strategy,
      resultCount: scoredResults.length,
    });

    let finalOutput: string;

    switch (strategy) {
      case 'weighted_consensus':
        finalOutput = this.weightedConsensusMerge(scoredResults);
        break;
      case 'best_pick':
        finalOutput = this.bestPickMerge(scoredResults);
        break;
      case 'hierarchical_merge':
        finalOutput = this.hierarchicalMerge(scoredResults);
        break;
      default:
        finalOutput = this.weightedConsensusMerge(scoredResults);
    }

    const validationDetails = this.validateMergedOutput(finalOutput, scoredResults);
    const validationScore = validationDetails.reduce((sum, d) => sum + d.score, 0) / validationDetails.length;
    const validationPassed = validationScore >= 0.6 && validationDetails.every((d) => d.score > 0.3);

    const merged: MergedOutput = {
      taskId,
      finalOutput,
      contributingAgents: scoredResults.map((r) => r.agentId),
      mergeStrategy: strategy,
      validationScore: Math.round(validationScore * 10000) / 10000,
      validationPassed,
      validationDetails,
      mergedAt: Date.now(),
    };

    logger.info('Merge complete', {
      taskId,
      validationScore: merged.validationScore,
      validationPassed: merged.validationPassed,
      contributingAgents: merged.contributingAgents.length,
    });

    return merged;
  }

  private weightedConsensusMerge(results: ScoredResult[]): string {
    const totalScore = results.reduce((sum, r) => sum + r.finalScore, 0);
    const sections: string[] = [];

    sections.push('=== FRACTAL INFERENCE SWARM — MERGED OUTPUT ===\n');
    sections.push(`Strategy: Weighted Consensus | Agents: ${results.length} | Generated: ${new Date().toISOString()}\n`);
    sections.push('--- SYNTHESIS ---\n');

    const topResults = results
      .filter((r) => r.finalScore >= totalScore / results.length * 0.5)
      .sort((a, b) => b.finalScore - a.finalScore);

    if (topResults.length > 0) {
      const primaryAgent = topResults[0];
      sections.push(`[Primary Output — Agent ${primaryAgent.agentId.slice(0, 8)}, Score: ${primaryAgent.finalScore.toFixed(4)}, Weight: ${(primaryAgent.finalScore / totalScore * 100).toFixed(1)}%]\n`);
      sections.push(primaryAgent.output);
      sections.push('');

      if (topResults.length > 1) {
        sections.push('\n--- SUPPLEMENTARY CONTRIBUTIONS ---\n');
        for (let i = 1; i < topResults.length; i++) {
          const agent = topResults[i];
          const weight = (agent.finalScore / totalScore * 100).toFixed(1);
          sections.push(`[Agent ${agent.agentId.slice(0, 8)}, Score: ${agent.finalScore.toFixed(4)}, Weight: ${weight}%]`);
          sections.push(agent.output);
          sections.push('');
        }
      }
    }

    sections.push('\n--- CONSENSUS METRICS ---');
    sections.push(`Total Contributing Agents: ${topResults.length}/${results.length}`);
    sections.push(`Average Confidence: ${(results.reduce((s, r) => s + r.confidence, 0) / results.length).toFixed(4)}`);
    sections.push(`Score Spread: ${(results[0].finalScore - results[results.length - 1].finalScore).toFixed(4)}`);

    return sections.join('\n');
  }

  private bestPickMerge(results: ScoredResult[]): string {
    const best = results[0];
    const sections: string[] = [];

    sections.push('=== FRACTAL INFERENCE SWARM — MERGED OUTPUT ===\n');
    sections.push(`Strategy: Best Pick | Selected Agent: ${best.agentId.slice(0, 8)} | Score: ${best.finalScore.toFixed(4)}\n`);
    sections.push('--- OUTPUT ---\n');
    sections.push(best.output);
    sections.push('\n--- SELECTION RATIONALE ---');
    sections.push(`Selected agent ranked #1 out of ${results.length} agents`);
    sections.push(`Confidence: ${best.confidence.toFixed(4)}`);
    sections.push(`Reliability: ${best.reliabilityScore.toFixed(4)}`);
    sections.push(`Compute Time: ${best.computeTimeMs}ms`);

    return sections.join('\n');
  }

  private hierarchicalMerge(results: ScoredResult[]): string {
    const tiers = this.assignTiers(results);
    const sections: string[] = [];

    sections.push('=== FRACTAL INFERENCE SWARM — MERGED OUTPUT ===\n');
    sections.push(`Strategy: Hierarchical Merge | Agents: ${results.length} | Tiers: ${Object.keys(tiers).length}\n`);

    for (const [tier, tierResults] of Object.entries(tiers)) {
      sections.push(`\n--- TIER ${tier.toUpperCase()} ---\n`);
      for (const result of tierResults) {
        sections.push(`[Agent ${result.agentId.slice(0, 8)}, Score: ${result.finalScore.toFixed(4)}]`);
        sections.push(result.output);
        sections.push('');
      }
    }

    sections.push('\n--- HIERARCHY SUMMARY ---');
    for (const [tier, tierResults] of Object.entries(tiers)) {
      sections.push(`${tier}: ${tierResults.length} agents, avg score: ${(tierResults.reduce((s, r) => s + r.finalScore, 0) / tierResults.length).toFixed(4)}`);
    }

    return sections.join('\n');
  }

  private assignTiers(results: ScoredResult[]): Record<string, ScoredResult[]> {
    const tiers: Record<string, ScoredResult[]> = { primary: [], secondary: [], tertiary: [] };
    const maxScore = results[0]?.finalScore || 1;

    for (const result of results) {
      const ratio = result.finalScore / maxScore;
      if (ratio >= 0.8) {
        tiers.primary.push(result);
      } else if (ratio >= 0.5) {
        tiers.secondary.push(result);
      } else {
        tiers.tertiary.push(result);
      }
    }

    return Object.fromEntries(
      Object.entries(tiers).filter(([, v]) => v.length > 0)
    );
  }

  private validateMergedOutput(output: string, results: ScoredResult[]): ValidationDetail[] {
    const details: ValidationDetail[] = [];

    const hasContent = output.length > 100;
    details.push({
      criterion: 'content_completeness',
      passed: hasContent,
      score: hasContent ? Math.min(1, output.length / 500) : 0.1,
      message: hasContent ? 'Output contains substantial content' : 'Output is too short',
    });

    const avgConfidence = results.reduce((s, r) => s + r.confidence, 0) / results.length;
    details.push({
      criterion: 'agent_confidence',
      passed: avgConfidence >= 0.5,
      score: avgConfidence,
      message: `Average agent confidence: ${avgConfidence.toFixed(4)}`,
    });

    const topAgentWeight = results[0]?.finalScore / results.reduce((s, r) => s + r.finalScore, 0);
    const diversityScore = 1 - (topAgentWeight || 1);
    details.push({
      criterion: 'output_diversity',
      passed: diversityScore >= 0.2,
      score: Math.min(1, diversityScore * 2),
      message: `Source diversity: ${(diversityScore * 100).toFixed(1)}% — ${diversityScore >= 0.2 ? 'multiple agents contributed' : 'dominated by single agent'}`,
    });

    const allConverged = results.every((r) => r.inferenceMetadata.convergenceReached);
    details.push({
      criterion: 'convergence_check',
      passed: allConverged,
      score: allConverged ? 1 : results.filter((r) => r.inferenceMetadata.convergenceReached).length / results.length,
      message: allConverged ? 'All agents reached convergence' : 'Some agents did not converge',
    });

    const scoreSpread = results[0]?.finalScore - results[results.length - 1]?.finalScore;
    const consistencyScore = Math.max(0, 1 - scoreSpread * 2);
    details.push({
      criterion: 'score_consistency',
      passed: consistencyScore >= 0.4,
      score: consistencyScore,
      message: `Score spread: ${scoreSpread.toFixed(4)} — ${consistencyScore >= 0.4 ? 'consistent' : 'high variance'}`,
    });

    return details;
  }
}

export const mergeEngine = new MergeEngine();