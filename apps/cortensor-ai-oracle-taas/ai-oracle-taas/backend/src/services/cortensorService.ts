import axios, { type AxiosInstance } from "axios"
import { logger } from "../utils/logger"
import type { MinerResponse, QueryOptions, Miner } from "../types"

export class CortensorService {
  private client: AxiosInstance
  private apiKey: string
  private baseURL: string

  constructor() {
    this.apiKey = process.env.CORTENSOR_API_KEY || ""
    this.baseURL = process.env.CORTENSOR_API_ENDPOINT || "http://localhost:8080"

    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 60000,
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
    })

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        logger.info(`Cortensor API Request: ${config.method?.toUpperCase()} ${config.url}`)
        return config
      },
      (error) => {
        logger.error("Cortensor API Request Error:", error)
        return Promise.reject(error)
      },
    )

    // Response interceptor for logging
    this.client.interceptors.response.use(
      (response) => {
        logger.info(`Cortensor API Response: ${response.status} ${response.config.url}`)
        return response
      },
      (error) => {
        logger.error("Cortensor API Response Error:", error.response?.data || error.message)
        return Promise.reject(error)
      },
    )
  }

  async getAvailableMiners(criteria?: {
    specialization?: string
    minReputation?: number
    maxResponseTime?: number
  }): Promise<Miner[]> {
    try {
      const response = await this.client.get("/miners", {
        params: criteria,
      })

      return response.data.miners || []
    } catch (error) {
      logger.error("Failed to get available miners:", error)
      // Return mock miners for development
      return this.getMockMiners()
    }
  }

  async queryMultipleMiners(query: string, minerIds: string[], options: QueryOptions): Promise<MinerResponse[]> {
    const responses: MinerResponse[] = []
    const promises = minerIds.map((minerId) => this.querySingleMiner(query, minerId, options))

    try {
      const results = await Promise.allSettled(promises)

      results.forEach((result, index) => {
        if (result.status === "fulfilled" && result.value) {
          responses.push(result.value)
        } else {
          logger.warn(
            `Miner ${minerIds[index]} failed:`,
            result.status === "rejected" ? result.reason : "Unknown error",
          )
        }
      })

      return responses
    } catch (error) {
      logger.error("Failed to query multiple miners:", error)
      throw error
    }
  }

  private async querySingleMiner(query: string, minerId: string, options: QueryOptions): Promise<MinerResponse | null> {
    const startTime = Date.now()

    try {
      const response = await this.client.post(
        `/miners/${minerId}/inference`,
        {
          prompt: query,
          max_tokens: options.maxTokens || 500,
          temperature: options.temperature || 0.7,
          timeout: options.timeoutMs || 30000,
        },
        {
          timeout: options.timeoutMs || 30000,
        },
      )

      const responseTime = Date.now() - startTime

      return {
        minerId,
        response: response.data.text || response.data.response,
        confidence: response.data.confidence || 0.8,
        responseTime,
        reputation: await this.getMinerReputation(minerId),
        sources: response.data.sources || [],
        metadata: {
          model: response.data.model,
          tokens_used: response.data.tokens_used,
        },
      }
    } catch (error) {
      logger.error(`Failed to query miner ${minerId}:`, error)

      // Return mock response for development
      if (process.env.NODE_ENV === "development") {
        return this.getMockMinerResponse(minerId, query)
      }

      return null
    }
  }

  async getMinerReputation(minerId: string): Promise<number> {
    try {
      const response = await this.client.get(`/miners/${minerId}/reputation`)
      return response.data.reputation || 0.5
    } catch (error) {
      logger.warn(`Failed to get reputation for miner ${minerId}:`, error)
      return 0.5 // Default reputation
    }
  }

  async updateMinerReputation(minerId: string, newReputation: number): Promise<void> {
    try {
      await this.client.post(`/miners/${minerId}/reputation`, {
        reputation: newReputation,
      })
      logger.info(`Updated reputation for miner ${minerId}: ${newReputation}`)
    } catch (error) {
      logger.error(`Failed to update reputation for miner ${minerId}:`, error)
    }
  }

  // Mock methods for development
  private getMockMiners(): Miner[] {
    return [
      {
        id: "miner_001",
        name: "General AI Miner 1",
        endpoint: "http://miner1.cortensor.network",
        reputation: 0.85,
        specializations: ["general", "factual"],
        isActive: true,
        averageResponseTime: 2500,
      },
      {
        id: "miner_002",
        name: "Math Specialist Miner",
        endpoint: "http://miner2.cortensor.network",
        reputation: 0.92,
        specializations: ["calculation", "analysis"],
        isActive: true,
        averageResponseTime: 1800,
      },
      {
        id: "miner_003",
        name: "Opinion Analysis Miner",
        endpoint: "http://miner3.cortensor.network",
        reputation: 0.78,
        specializations: ["opinion", "prediction"],
        isActive: true,
        averageResponseTime: 3200,
      },
    ]
  }

  private getMockMinerResponse(minerId: string, query: string): MinerResponse {
    const responses = {
      miner_001: `Based on available information, ${query.toLowerCase()} appears to be factually accurate. This conclusion is drawn from multiple reliable sources and cross-referenced data.`,
      miner_002: `From a mathematical/analytical perspective, ${query.toLowerCase()} can be verified through computational methods and statistical analysis.`,
      miner_003: `In terms of general consensus and opinion analysis, ${query.toLowerCase()} aligns with majority viewpoints and expert opinions in the field.`,
    }

    return {
      minerId,
      response: responses[minerId as keyof typeof responses] || `Response to: ${query}`,
      confidence: 0.75 + Math.random() * 0.2,
      responseTime: 1500 + Math.random() * 2000,
      reputation: 0.7 + Math.random() * 0.25,
      sources: ["https://example.com/source1", "https://example.com/source2"],
      metadata: {
        model: "cortensor-v1",
        tokens_used: 150,
      },
    }
  }
}

export const cortensorService = new CortensorService()
