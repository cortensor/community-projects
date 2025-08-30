import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001/api';

export interface AnalyzeRequest {
  claim: string;
  type: 'text' | 'url';
  options?: {
    minMiners?: number;
    timeout?: number;
  };
}

export interface MinerResponse {
  minerId: string;
  score: number;
  reasoning: string;
  sources: string[];
}

export interface SupportingSource {
  url: string;
  title: string;
  credibility: number;
  excerpt: string;
  domain: string;
}

export interface AnalysisResult {
  credibilityScore: number;
  confidence: number;
  isCredible: boolean;
  consensus: string;
  supportingSources: SupportingSource[];
  minerResponses: MinerResponse[];
}

export interface AnalyzeResponse {
  success: boolean;
  data: {
    claim: string;
    type: string;
    analysis: AnalysisResult;
    metadata: {
      processedAt: string;
      minerCount: number;
      processingTimeMs: number;
    };
  };
  error?: string;
}

export interface BackendStatus {
  success: boolean;
  data: {
    cortensorConnected: boolean;
    availableMiners: number;
    lastHealthCheck: string | null;
  };
}

export class TruthLensApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 60000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        console.log('API Request:', config.method?.toUpperCase(), config.url);
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    this.client.interceptors.response.use(
      (response) => {
        console.log('API Response:', response.status, response.config.url);
        return response;
      },
      (error) => {
        console.error('API Response Error:', {
          status: error.response?.status,
          message: error.message,
          url: error.config?.url,
        });
        return Promise.reject(error);
      }
    );
  }

  async analyzeClaim(request: AnalyzeRequest): Promise<AnalysisResult> {
    try {
      const response = await this.client.post<AnalyzeResponse>('/analysis/analyze', request);
      
      if (!response.data.success) {
        throw new Error(response.data.error || 'Analysis failed');
      }

      return response.data.data.analysis;
    } catch (error) {
      console.error('Failed to analyze claim:', error);
      
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 400) {
          throw new Error('Invalid request. Please check your input.');
        } else if (error.response?.status === 429) {
          throw new Error('Too many requests. Please try again later.');
        } else if (error.response?.status >= 500) {
          throw new Error('Server error. Please try again later.');
        }
      }
      
      // Check if it's a network error (backend not running)
      if (error instanceof Error && error.message.includes('ECONNREFUSED')) {
        throw new Error('Unable to connect to TruthLens backend. Please ensure the backend server is running.');
      }
      
      throw new Error('Failed to analyze claim. Please try again.');
    }
  }

  async getStatus(): Promise<BackendStatus['data']> {
    try {
      const response = await this.client.get<BackendStatus>('/analysis/status');
      
      if (!response.data.success) {
        throw new Error('Failed to get backend status');
      }

      return response.data.data;
    } catch (error) {
      console.error('Failed to get backend status:', error);
      throw new Error('Unable to check backend status');
    }
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.status === 200;
    } catch {
      return false;
    }
  }
}

// Singleton instance
export const truthLensApi = new TruthLensApiService();
