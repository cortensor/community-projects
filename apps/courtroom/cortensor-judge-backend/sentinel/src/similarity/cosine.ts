/**
 * Cosine Similarity Vector Analysis
 * Used to detect deviations between miner outputs
 */

import { SimilarityResult } from '../types/evidence';

/**
 * Calculate cosine similarity between two vectors
 * Used to compare AI output embeddings
 */
export function cosineSimilarity(
  vectorA: number[],
  vectorB: number[]
): number {
  if (vectorA.length !== vectorB.length) {
    throw new Error('Vectors must have same length');
  }

  if (vectorA.length === 0) {
    return 1; // Empty vectors are identical
  }

  // Calculate dot product
  let dotProduct = 0;
  let magnitudeA = 0;
  let magnitudeB = 0;

  for (let i = 0; i < vectorA.length; i++) {
    dotProduct += vectorA[i] * vectorB[i];
    magnitudeA += vectorA[i] * vectorA[i];
    magnitudeB += vectorB[i] * vectorB[i];
  }

  magnitudeA = Math.sqrt(magnitudeA);
  magnitudeB = Math.sqrt(magnitudeB);

  // Avoid division by zero
  if (magnitudeA === 0 || magnitudeB === 0) {
    return 0;
  }

  return dotProduct / (magnitudeA * magnitudeB);
}

/**
 * Compare two text outputs using vector embeddings
 * Returns similarity score and analysis
 */
export async function compareOutputs(
  output1: string,
  output2: string,
  embeddingModel: EmbeddingModel
): Promise<SimilarityResult> {
  try {
    // Get embeddings for both outputs
    const [vector1, vector2] = await Promise.all([
      embeddingModel.embed(output1),
      embeddingModel.embed(output2),
    ]);

    // Calculate similarity
    const score = cosineSimilarity(vector1, vector2);

    return {
      score,
      vectorA: vector1,
      vectorB: vector2,
      isDifferent: score < 0.95, // Threshold configurable
    };
  } catch (error) {
    console.error('Error comparing outputs:', error);
    throw error;
  }
}

/**
 * Compare multiple outputs and find deviations
 * Used to detect if one miner is providing incorrect answer
 */
export async function detectOutliers(
  outputs: Map<string, string>, // minerAddress -> output
  embeddingModel: EmbeddingModel,
  threshold: number = 0.90
): Promise<{
  outliers: string[]; // Miner addresses with different outputs
  consensusGroup: string[];
  scores: Map<string, number>;
}> {
  const miners = Array.from(outputs.keys());

  if (miners.length < 2) {
    return {
      outliers: [],
      consensusGroup: miners,
      scores: new Map(),
    };
  }

  // Get embeddings for all outputs
  const embeddings = new Map<string, number[]>();
  for (const [miner, output] of outputs) {
    const vector = await embeddingModel.embed(output);
    embeddings.set(miner, vector);
  }

  // Calculate pairwise similarities
  const similarityMatrix = new Map<string, number>();
  for (let i = 0; i < miners.length; i++) {
    for (let j = i + 1; j < miners.length; j++) {
      const minerA = miners[i];
      const minerB = miners[j];
      const vectorA = embeddings.get(minerA)!;
      const vectorB = embeddings.get(minerB)!;
      const similarity = cosineSimilarity(vectorA, vectorB);
      similarityMatrix.set(`${minerA}:${minerB}`, similarity);
    }
  }

  // Find consensus group (most similar miners)
  const similarityScores = new Map<string, number[]>();
  for (const miner of miners) {
    similarityScores.set(miner, []);
  }

  for (const [pair, similarity] of similarityMatrix) {
    const [minerA, minerB] = pair.split(':');
    similarityScores.get(minerA)!.push(similarity);
    similarityScores.get(minerB)!.push(similarity);
  }

  // Calculate average similarity for each miner
  const avgSimilarities = new Map<string, number>();
  for (const [miner, scores] of similarityScores) {
    const avg = scores.length > 0 ? scores.reduce((a, b) => a + b) / scores.length : 1;
    avgSimilarities.set(miner, avg);
  }

  // Identify outliers
  const consensusMean =
    Array.from(avgSimilarities.values()).reduce((a, b) => a + b) / miners.length;
  const stdDev = calculateStdDev(Array.from(avgSimilarities.values()), consensusMean);

  const outliers: string[] = [];
  for (const [miner, avgSim] of avgSimilarities) {
    if (avgSim < consensusMean - stdDev) {
      outliers.push(miner);
    }
  }

  const consensusGroup = miners.filter((m) => !outliers.includes(m));

  return {
    outliers,
    consensusGroup,
    scores: avgSimilarities,
  };
}

/**
 * Calculate standard deviation
 */
function calculateStdDev(values: number[], mean: number): number {
  if (values.length === 0) return 0;
  const squaredDiffs = values.map((v) => Math.pow(v - mean, 2));
  const variance = squaredDiffs.reduce((a, b) => a + b) / values.length;
  return Math.sqrt(variance);
}

/**
 * Embedding model interface
 * Can be implemented with different providers (Pinecone, OpenAI, etc.)
 */
export interface EmbeddingModel {
  embed(text: string): Promise<number[]>;
  embedBatch(texts: string[]): Promise<number[][]>;
}

/**
 * Simple mock embedding model for testing
 */
export class MockEmbedding implements EmbeddingModel {
  private cache = new Map<string, number[]>();

  async embed(text: string): Promise<number[]> {
    if (this.cache.has(text)) {
      return this.cache.get(text)!;
    }

    // Generate deterministic vector based on text hash
    const hash = this.simpleHash(text);
    const vector = this.generateVector(hash, 1536);
    this.cache.set(text, vector);
    return vector;
  }

  async embedBatch(texts: string[]): Promise<number[][]> {
    return Promise.all(texts.map((t) => this.embed(t)));
  }

  private simpleHash(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash);
  }

  private generateVector(seed: number, dimension: number): number[] {
    const vector: number[] = [];
    for (let i = 0; i < dimension; i++) {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      vector.push((seed % 1000) / 1000 - 0.5);
    }
    return vector;
  }
}
