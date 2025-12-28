/**
 * Cortensor Router - Interface to decentralized AI network
 * Handles calls to the Cortensor /validate endpoint for multi-node consensus
 */

import axios, { AxiosInstance } from 'axios';
import { config } from '../config/env';

export interface CortensorInferenceRequest {
  prompt: string;
  modelId: string;
  modelName: string;
  chainOfThought?: boolean;
}

export interface CortensorValidateRequest {
  prompt: string;
  expectedAnswer?: string;
  validators?: number;
}

export interface CortensorInferenceResponse {
  result: string;
  modelId: string;
  modelName: string;
  logicTrace: string[];
  poiHash: string;
  minerAddress: string;
  timestamp: number;
  confidence: number;
  modelHash: string;
}

export interface CortensorValidateResponse {
  isValid: boolean;
  consensusScore: number;
  validatorCount: number;
  results: CortensorInferenceResponse[];
  averageConfidence: number;
  poiSignature: string;
}

/**
 * CortensorRouter handles all interactions with the Cortensor network
 */
export class CortensorRouter {
  private client: AxiosInstance;
  private apiKey: string;

  constructor(
    private apiUrl: string = config.CORTENSOR_API_URL,
    apiKey: string = config.CORTENSOR_API_KEY
  ) {
    this.apiKey = apiKey;

    this.client = axios.create({
      baseURL: apiUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
      },
    });
  }

  /**
   * Run inference through Cortensor network
   * Gets a single response from the network
   */
  async runInference(
    request: CortensorInferenceRequest
  ): Promise<CortensorInferenceResponse> {
    try {
      const response = await this.client.post<CortensorInferenceResponse>(
        '/inference',
        {
          prompt: request.prompt,
          model_id: request.modelId,
          model_name: request.modelName,
          chain_of_thought: request.chainOfThought ?? true,
        }
      );

      return response.data;
    } catch (error) {
      console.error('Cortensor inference failed:', error);
      throw new Error(`Cortensor inference error: ${error}`);
    }
  }

  /**
   * Run /validate endpoint for multi-node consensus
   * Critical for detecting deviations across miners
   */
  async validateInference(
    request: CortensorValidateRequest
  ): Promise<CortensorValidateResponse> {
    try {
      const response = await this.client.post<CortensorValidateResponse>(
        '/validate',
        {
          prompt: request.prompt,
          expected_answer: request.expectedAnswer,
          validators: request.validators ?? 3,
        }
      );

      return response.data;
    } catch (error) {
      console.error('Cortensor validation failed:', error);
      throw new Error(`Cortensor validation error: ${error}`);
    }
  }

  /**
   * Get miner reputation from Cortensor network
   */
  async getMinerReputation(minerAddress: string): Promise<{
    reputation: number;
    successRate: number;
    totalInferences: number;
  }> {
    try {
      const response = await this.client.get(
        `/miner/${minerAddress}/reputation`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to fetch miner reputation:', error);
      throw error;
    }
  }

  /**
   * Health check for Cortensor network
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.status === 200;
    } catch (error) {
      console.error('Cortensor health check failed:', error);
      return false;
    }
  }

  /**
   * Batch validate multiple prompts
   */
  async batchValidate(
    requests: CortensorValidateRequest[]
  ): Promise<CortensorValidateResponse[]> {
    try {
      const response = await this.client.post<CortensorValidateResponse[]>(
        '/batch-validate',
        {
          requests: requests.map((r) => ({
            prompt: r.prompt,
            expected_answer: r.expectedAnswer,
            validators: r.validators ?? 3,
          })),
        }
      );

      return response.data;
    } catch (error) {
      console.error('Batch validation failed:', error);
      throw error;
    }
  }

  /**
   * Get recent inference activity (for monitoring)
   */
  async getRecentActivity(
    limit: number = 100,
    offset: number = 0
  ): Promise<CortensorInferenceResponse[]> {
    try {
      const response = await this.client.get<CortensorInferenceResponse[]>(
        '/recent-activity',
        {
          params: { limit, offset },
        }
      );

      return response.data;
    } catch (error) {
      console.error('Failed to fetch recent activity:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const cortensorRouter = new CortensorRouter();
