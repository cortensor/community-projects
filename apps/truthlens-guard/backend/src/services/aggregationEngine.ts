import { MinerResponse, SupportingSource } from './cortensorService';
import { logger } from '../utils/logger';

export interface AggregatedResult {
  credibilityScore: number;
  confidence: number;
  isCredible: boolean;
  consensus: string;
  supportingSources: SupportingSource[];
  processingTimeMs: number;
}

export class AggregationEngine {
  
  aggregateResponses(responses: MinerResponse[]): AggregatedResult {
    const startTime = Date.now();
    
    if (responses.length === 0) {
      throw new Error('No miner responses to aggregate');
    }

    logger.info('Aggregating miner responses', {
      responseCount: responses.length
    });

    // Calculate credibility score using robust median approach
    const credibilityScore = this.calculateRobustScore(responses);
    
    // Calculate overall confidence
    const confidence = this.calculateConfidence(responses);
    
    // Determine if claim is credible
    const isCredible = credibilityScore >= 0.6;
    
    // Generate consensus summary
    const consensus = this.generateConsensus(responses, credibilityScore);
    
    // Extract and rank supporting sources
    const supportingSources = this.extractSupportingSources(responses);
    
    const processingTimeMs = Date.now() - startTime;

    const result: AggregatedResult = {
      credibilityScore,
      confidence,
      isCredible,
      consensus,
      supportingSources,
      processingTimeMs
    };

    logger.info('Response aggregation completed', {
      credibilityScore,
      confidence,
      isCredible,
      sourceCount: supportingSources.length,
      processingTimeMs
    });

    return result;
  }

  private calculateRobustScore(responses: MinerResponse[]): number {
    // Use median score to resist outliers and malicious miners
    const scores = responses.map(r => r.score).sort((a, b) => a - b);
    
    if (scores.length === 0) return 0.5;
    
    const median = scores.length % 2 === 0
      ? (scores[scores.length / 2 - 1] + scores[scores.length / 2]) / 2
      : scores[Math.floor(scores.length / 2)];

    // Apply confidence weighting
    const weightedSum = responses.reduce((sum, response) => {
      return sum + (response.score * response.confidence);
    }, 0);
    
    const totalConfidence = responses.reduce((sum, response) => {
      return sum + response.confidence;
    }, 0);

    const weightedAverage = totalConfidence > 0 ? weightedSum / totalConfidence : median;
    
    // Combine median (70%) and weighted average (30%) for robustness
    return (median * 0.7) + (weightedAverage * 0.3);
  }

  private calculateConfidence(responses: MinerResponse[]): number {
    if (responses.length === 0) return 0;

    // Calculate variance in scores
    const scores = responses.map(r => r.score);
    const mean = scores.reduce((sum, score) => sum + score, 0) / scores.length;
    const variance = scores.reduce((sum, score) => sum + Math.pow(score - mean, 2), 0) / scores.length;
    const standardDeviation = Math.sqrt(variance);

    // Lower variance = higher confidence
    const varianceConfidence = Math.max(0, 1 - (standardDeviation * 2));

    // Average miner confidence
    const avgMinerConfidence = responses.reduce((sum, r) => sum + r.confidence, 0) / responses.length;

    // Sample size confidence (more miners = more confidence)
    const sampleSizeConfidence = Math.min(1, responses.length / 10);

    // Combined confidence score
    return (varianceConfidence * 0.4) + (avgMinerConfidence * 0.4) + (sampleSizeConfidence * 0.2);
  }

  private generateConsensus(responses: MinerResponse[], credibilityScore: number): string {
    const minerCount = responses.length;
    const highScoreCount = responses.filter(r => r.score >= 0.7).length;
    const lowScoreCount = responses.filter(r => r.score <= 0.3).length;
    
    let consensusText = `Based on analysis from ${minerCount} independent AI miners, `;

    if (credibilityScore >= 0.8) {
      consensusText += `this claim shows strong credibility with ${highScoreCount} miners providing high confidence scores. `;
    } else if (credibilityScore >= 0.6) {
      consensusText += `this claim appears generally credible with moderate consensus across miners. `;
    } else if (credibilityScore >= 0.4) {
      consensusText += `this claim shows mixed credibility with conflicting evidence reported by miners. `;
    } else if (credibilityScore >= 0.2) {
      consensusText += `this claim shows low credibility with ${lowScoreCount} miners reporting significant concerns. `;
    } else {
      consensusText += `this claim shows very low credibility with strong consensus against its veracity. `;
    }

    // Add most common reasoning themes
    const reasoningThemes = this.extractReasoningThemes(responses);
    if (reasoningThemes.length > 0) {
      consensusText += `Key factors include: ${reasoningThemes.slice(0, 3).join(', ')}.`;
    }

    return consensusText;
  }

  private extractReasoningThemes(responses: MinerResponse[]): string[] {
    const themes: { [key: string]: number } = {};
    
    const commonTerms = [
      'reliable sources', 'factual accuracy', 'evidence quality',
      'source verification', 'contradictory information', 'insufficient evidence',
      'corroboration', 'fact-checking', 'peer review', 'expert consensus'
    ];

    responses.forEach(response => {
      const reasoning = response.reasoning.toLowerCase();
      commonTerms.forEach(term => {
        if (reasoning.includes(term)) {
          themes[term] = (themes[term] || 0) + 1;
        }
      });
    });

    return Object.entries(themes)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([theme]) => theme);
  }

  private extractSupportingSources(responses: MinerResponse[]): SupportingSource[] {
    const sourceMap = new Map<string, SupportingSource>();
    
    responses.forEach(response => {
      response.sources.forEach(sourceUrl => {
        if (sourceMap.has(sourceUrl)) {
          const existing = sourceMap.get(sourceUrl)!;
          existing.credibility = (existing.credibility + response.score) / 2;
        } else {
          sourceMap.set(sourceUrl, {
            url: sourceUrl,
            title: this.generateSourceTitle(sourceUrl),
            credibility: response.score,
            excerpt: this.generateSourceExcerpt(response.reasoning),
            domain: this.extractDomain(sourceUrl)
          });
        }
      });
    });

    return Array.from(sourceMap.values())
      .sort((a, b) => b.credibility - a.credibility)
      .slice(0, 10); // Top 10 sources
  }

  private generateSourceTitle(url: string): string {
    const domain = this.extractDomain(url);
    const domainTitles: { [key: string]: string } = {
      'reuters.com': 'Reuters News Report',
      'apnews.com': 'Associated Press Article',
      'bbc.com': 'BBC News Analysis',
      'npr.org': 'NPR Investigation',
      'snopes.com': 'Snopes Fact Check',
      'factcheck.org': 'FactCheck.org Verification',
      'politifact.com': 'PolitiFact Analysis',
      'nature.com': 'Nature Scientific Paper',
      'sciencemag.org': 'Science Magazine Study',
      'nejm.org': 'New England Journal of Medicine'
    };

    return domainTitles[domain] || `${domain} - Source Verification`;
  }

  private generateSourceExcerpt(reasoning: string): string {
    // Extract first meaningful sentence from reasoning
    const sentences = reasoning.split('.').filter(s => s.trim().length > 10);
    return sentences[0]?.trim() + '.' || 'Supporting evidence found through verification process.';
  }

  private extractDomain(url: string): string {
    try {
      // Handle URLs that might not have protocol
      const fullUrl = url.startsWith('http') ? url : `https://${url}`;
      return new URL(fullUrl).hostname;
    } catch {
      // If URL parsing fails, extract domain manually
      return url.replace(/^https?:\/\//, '').split('/')[0];
    }
  }
}
