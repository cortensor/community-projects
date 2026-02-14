/**
 * API Client Service
 * Handles all HTTP requests to the backend
 */

import axios, { AxiosInstance } from 'axios';
import { API_CONFIG } from '@/config/api';

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('[API] Request error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        return response;
      },
      (error) => {
        console.error('[API] Response error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<ApiResponse> {
    try {
      const response = await this.client.get(API_CONFIG.ENDPOINTS.HEALTH);
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Get dispute by ID
   */
  async getDispute(disputeId: string): Promise<ApiResponse> {
    try {
      const response = await this.client.get(API_CONFIG.ENDPOINTS.DISPUTE(disputeId));
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Get miner trust score
   */
  async getMinerTrustScore(minerAddress: string): Promise<ApiResponse<{ minerAddress: string; trustScore: number }>> {
    try {
      const response = await this.client.get(API_CONFIG.ENDPOINTS.MINER_TRUST_SCORE(minerAddress));
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Initiate challenge
   */
  async initiateChallenge(evidence: any, bondAmount: string): Promise<ApiResponse> {
    try {
      const response = await this.client.post(API_CONFIG.ENDPOINTS.CHALLENGE, {
        evidence,
        bondAmount,
      });
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Monitor for suspicious outputs
   */
  async monitorOutput(prompt: string, threshold: number = 95): Promise<ApiResponse> {
    try {
      const response = await this.client.post(API_CONFIG.ENDPOINTS.MONITOR, {
        prompt,
        threshold,
      });
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Auto-challenge if suspicious
   */
  async autoChallenge(evidence: any, minBond: string, maxBond: string): Promise<ApiResponse> {
    try {
      const response = await this.client.post(API_CONFIG.ENDPOINTS.AUTO_CHALLENGE, {
        evidence,
        minBond,
        maxBond,
      });
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Generate verdict
   */
  async generateVerdict(disputeId: string, evidence: any, minerOutput: string): Promise<ApiResponse> {
    try {
      const response = await this.client.post(API_CONFIG.ENDPOINTS.VERDICT_GENERATE, {
        disputeId,
        evidence,
        minerOutput,
      });
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Submit verdict
   */
  async submitVerdict(disputeId: string, evidence: any, verdict: string, reasoning: string): Promise<ApiResponse> {
    try {
      const response = await this.client.post(API_CONFIG.ENDPOINTS.VERDICT_SUBMIT, {
        disputeId,
        evidence,
        verdict,
        reasoning,
      });
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Execute full verdict workflow
   */
  async executeVerdict(disputeId: string, evidence: any): Promise<ApiResponse> {
    try {
      const response = await this.client.post(API_CONFIG.ENDPOINTS.VERDICT_EXECUTE, {
        disputeId,
        evidence,
      });
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Settle dispute
   */
  async settleDispute(disputeId: string): Promise<ApiResponse> {
    try {
      const response = await this.client.post(API_CONFIG.ENDPOINTS.DISPUTE_SETTLE, {
        disputeId,
      });
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Get queue statistics
   */
  async getQueueStats(): Promise<ApiResponse> {
    try {
      const response = await this.client.get(API_CONFIG.ENDPOINTS.QUEUE_STATS);
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Generate test evidence (for testing)
   */
  async generateTestEvidence(prompt: string, minerAddress?: string): Promise<ApiResponse> {
    try {
      const response = await this.client.post(API_CONFIG.ENDPOINTS.TEST_GENERATE_EVIDENCE, {
        prompt,
        minerAddress,
      });
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }

  /**
   * Check Cortensor health
   */
  async checkCortensorHealth(): Promise<ApiResponse> {
    try {
      const response = await this.client.get(API_CONFIG.ENDPOINTS.TEST_HEALTH_CORTENSOR);
      return { success: true, data: response.data };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient();


