import { ResearchOrchestrator } from './ResearchOrchestrator';
import { WebSearchAgent } from './agents/WebSearchAgent';
import { streamManager } from './StreamManager';
import { 
  ResearchOptions, 
  ResearchSession, 
  StreamEvent,
  StreamEventType,
  ResearchReport 
} from '@/types/research';

/**
 * Main service for managing research operations
 */
export class ResearchService {
  private orchestrator: ResearchOrchestrator;
  private static instance: ResearchService;

  private constructor() {
    this.orchestrator = new ResearchOrchestrator();
    this.registerAgents();
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): ResearchService {
    if (!ResearchService.instance) {
      ResearchService.instance = new ResearchService();
    }
    return ResearchService.instance;
  }

  /**
   * Register available agents
   */
  private registerAgents(): void {
    // Register the web search agent
    this.orchestrator.registerAgent('web_search', WebSearchAgent as any);
    
    // TODO: Register other agents as they're implemented
    // this.orchestrator.registerAgent('deep_analysis', DeepAnalysisAgent);
    // this.orchestrator.registerAgent('fact_check', FactCheckAgent);
    // this.orchestrator.registerAgent('synthesis', SynthesisAgent);
  }

  /**
   * Start a new research session
   */
  public async startResearch(
    query: string,
    options?: ResearchOptions
  ): Promise<{ sessionId: string; estimatedTime: number }> {
    // Start the research
    const sessionId = await this.orchestrator.startResearch(query, options);
    
    // Set up streaming
    this.orchestrator.onStreamEvent(sessionId, (event: StreamEvent) => {
      streamManager.sendToStream(sessionId, event);
    });
    
    // Get initial session info
    const session = this.orchestrator.getSessionStatus(sessionId);
    const estimatedTime = session?.analysis?.estimatedTime || 30;
    
    return { sessionId, estimatedTime };
  }

  /**
   * Get research session status
   */
  public getSessionStatus(sessionId: string): ResearchSession | null {
    return this.orchestrator.getSessionStatus(sessionId);
  }

  /**
   * Create a stream for a session
   */
  public createStream(sessionId: string): ReadableStream {
    return streamManager.createStream(sessionId);
  }

  /**
   * Abort a research session
   */
  public async abortSession(sessionId: string): Promise<boolean> {
    const success = await this.orchestrator.abortSession(sessionId);
    
    if (success) {
      // Send abort event to stream
      streamManager.sendToStream(sessionId, {
        type: StreamEventType.SESSION_ABORTED,
        sessionId,
        timestamp: new Date(),
        data: { message: 'Session aborted by user' }
      } as StreamEvent);
      
      // Close the stream
      setTimeout(() => {
        streamManager.closeStream(sessionId);
      }, 1000);
    }
    
    return success;
  }

  /**
   * Get final report for a completed session
   */
  public getSessionReport(sessionId: string): ResearchReport | null {
    const session = this.orchestrator.getSessionStatus(sessionId);
    return session?.finalReport || null;
  }

  /**
   * Check if a session exists
   */
  public sessionExists(sessionId: string): boolean {
    return this.orchestrator.getSessionStatus(sessionId) !== null;
  }

  /**
   * Get all active sessions (for monitoring)
   */
  public getActiveSessions(): string[] {
    // This would need to be implemented in the orchestrator
    // For now, return empty array
    return [];
  }
}

// Export singleton instance
export const researchService = ResearchService.getInstance();