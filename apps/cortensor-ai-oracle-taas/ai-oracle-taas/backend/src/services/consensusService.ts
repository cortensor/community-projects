import type { MinerResponse, ConsensusResult, ConsensusAlgorithm } from "../types"
import { logger } from "../utils/logger.ts"
import * as natural from "natural"

export class ConsensusService {
  private algorithms: ConsensusAlgorithm[] = [
    new SemanticSimilarityConsensus(),
    new ReputationWeightedVoting(),
    new ConfidenceBasedAggregation(),
    new OutlierDetectionConsensus(),
  ]

  async buildConsensus(responses: MinerResponse[], threshold = 0.8): Promise<ConsensusResult> {
    if (responses.length === 0) {
      throw new Error("No responses provided for consensus building")
    }

    logger.info(`Building consensus from ${responses.length} miner responses`)

    // Run all consensus algorithms
    const algorithmResults = await Promise.all(
      this.algorithms.map(async (algorithm) => {
        try {
          const result = await algorithm.calculate(responses)
          return { algorithm: algorithm.name, result, weight: algorithm.weight }
        } catch (error) {
          logger.error(`Algorithm ${algorithm.name} failed:`, error)
          return null
        }
      }),
    )

    // Filter out failed algorithms
    const validResults = algorithmResults.filter((r) => r !== null)

    if (validResults.length === 0) {
      throw new Error("All consensus algorithms failed")
    }

    // Combine results using weighted average
    const finalConsensus = this.combineAlgorithmResults(validResults)

    // Check if consensus meets threshold
    const consensusReached = finalConsensus.consensusScore >= threshold

    return {
      consensusAnswer: finalConsensus.answer,
      consensusScore: finalConsensus.consensusScore,
      confidenceLevel: finalConsensus.confidenceLevel,
      algorithmResults: validResults.map((r) => ({
        name: r!.algorithm,
        score: r!.result.consensusScore,
        answer: r!.result.answer,
      })),
      consensusReached,
      participatingMiners: responses.length,
      outliers: finalConsensus.outliers || [],
      metadata: {
        threshold,
        processingTime: Date.now(),
        algorithmsUsed: validResults.length,
      },
    }
  }

  private combineAlgorithmResults(results: any[]): any {
    let totalWeight = 0
    let weightedScore = 0
    let weightedConfidence = 0
    const answers: { [key: string]: number } = {}

    // Calculate weighted scores and collect answers
    results.forEach(({ result, weight }) => {
      totalWeight += weight
      weightedScore += result.consensusScore * weight
      weightedConfidence += result.confidenceLevel * weight

      // Count answer frequency
      const answer = result.answer.toLowerCase().trim()
      answers[answer] = (answers[answer] || 0) + weight
    })

    // Find most weighted answer
    const finalAnswer = Object.entries(answers).sort(([, a], [, b]) => b - a)[0][0]

    return {
      answer: finalAnswer,
      consensusScore: weightedScore / totalWeight,
      confidenceLevel: weightedConfidence / totalWeight,
      outliers: [], // TODO: Implement outlier detection
    }
  }

  async detectHallucinations(responses: MinerResponse[]): Promise<any[]> {
    const hallucinations: any[] = []

    // Semantic similarity analysis
    for (let i = 0; i < responses.length; i++) {
      for (let j = i + 1; j < responses.length; j++) {
        // Fix: Add the required options parameter
        const similarity = natural.JaroWinklerDistance(
          responses[i].response, 
          responses[j].response, 
          { ignoreCase: true }
        )

        // If responses are very different, flag as potential hallucination
        if (similarity < 0.3) {
          hallucinations.push({
            type: "semantic_divergence",
            minerIds: [responses[i].minerId, responses[j].minerId],
            similarity,
            confidence: 1 - similarity,
          })
        }
      }
    }

    return hallucinations
  }
}

// Consensus Algorithm Implementations
class SemanticSimilarityConsensus implements ConsensusAlgorithm {
  name = "semantic_similarity"
  weight = 0.3

  async calculate(responses: MinerResponse[]): Promise<any> {
    const similarities: number[][] = []

    // Calculate pairwise similarities
    for (let i = 0; i < responses.length; i++) {
      similarities[i] = []
      for (let j = 0; j < responses.length; j++) {
        if (i === j) {
          similarities[i][j] = 1.0
        } else {
          similarities[i][j] = natural.JaroWinklerDistance(responses[i].response, responses[j].response, { ignoreCase: true })
        }
      }
    }

    // Find response with highest average similarity
    let bestIndex = 0
    let bestScore = 0

    for (let i = 0; i < responses.length; i++) {
      const avgSimilarity = similarities[i].reduce((a, b) => a + b, 0) / responses.length
      if (avgSimilarity > bestScore) {
        bestScore = avgSimilarity
        bestIndex = i
      }
    }

    return {
      answer: responses[bestIndex].response,
      consensusScore: bestScore,
      confidenceLevel: bestScore * 0.9,
    }
  }
}

class ReputationWeightedVoting implements ConsensusAlgorithm {
  name = "reputation_weighted"
  weight = 0.4

  async calculate(responses: MinerResponse[]): Promise<any> {
    // Group similar responses
    const responseGroups: { [key: string]: { responses: MinerResponse[]; totalReputation: number } } = {}

    responses.forEach((response) => {
      const key = response.response.toLowerCase().trim().substring(0, 100)
      if (!responseGroups[key]) {
        responseGroups[key] = { responses: [], totalReputation: 0 }
      }
      responseGroups[key].responses.push(response)
      responseGroups[key].totalReputation += response.reputation
    })

    // Find group with highest total reputation
    let bestGroup = null
    let bestReputation = 0

    Object.entries(responseGroups).forEach(([key, group]) => {
      if (group.totalReputation > bestReputation) {
        bestReputation = group.totalReputation
        bestGroup = group
      }
    })

    if (!bestGroup) {
      throw new Error("No valid response groups found")
    }

    const totalReputation = responses.reduce((sum, r) => sum + r.reputation, 0)
    const consensusScore = bestReputation / totalReputation

    return {
      answer: bestGroup.responses[0].response,
      consensusScore,
      confidenceLevel: consensusScore * 0.85,
    }
  }
}

class ConfidenceBasedAggregation implements ConsensusAlgorithm {
  name = "confidence_based"
  weight = 0.2

  async calculate(responses: MinerResponse[]): Promise<any> {
    // Sort by confidence
    const sortedResponses = responses.sort((a, b) => b.confidence - a.confidence)

    // Take top response by confidence
    const bestResponse = sortedResponses[0]
    const avgConfidence = responses.reduce((sum, r) => sum + r.confidence, 0) / responses.length

    return {
      answer: bestResponse.response,
      consensusScore: bestResponse.confidence,
      confidenceLevel: avgConfidence,
    }
  }
}

class OutlierDetectionConsensus implements ConsensusAlgorithm {
  name = "outlier_detection"
  weight = 0.1

  async calculate(responses: MinerResponse[]): Promise<any> {
    // Simple outlier detection based on response length and confidence
    const avgLength = responses.reduce((sum, r) => sum + r.response.length, 0) / responses.length
    const avgConfidence = responses.reduce((sum, r) => sum + r.confidence, 0) / responses.length

    const filtered = responses.filter((r) => {
      const lengthDiff = Math.abs(r.response.length - avgLength) / avgLength
      const confidenceDiff = Math.abs(r.confidence - avgConfidence) / avgConfidence

      return lengthDiff < 0.5 && confidenceDiff < 0.3 // Not too different from average
    })

    if (filtered.length === 0) {
      return {
        answer: responses[0].response,
        consensusScore: 0.5,
        confidenceLevel: 0.5,
      }
    }

    // Return most confident non-outlier
    const best = filtered.sort((a, b) => b.confidence - a.confidence)[0]

    return {
      answer: best.response,
      consensusScore: filtered.length / responses.length,
      confidenceLevel: best.confidence,
    }
  }
}

export const consensusService = new ConsensusService()
