import { 
  AgentType, 
  AgentStatus, 
  AgentTask, 
  AgentResult, 
  Finding,
  StreamEvent,
  StreamEventType 
} from '@/types/research';
import { generateId } from '@/lib/utils';

export abstract class ResearchAgent {
  public readonly id: string;
  public readonly type: AgentType;
  public status: AgentStatus = 'idle';
  public progress: number = 0;
  public currentTask?: string;
  protected sessionId: string = '';
  protected onStreamEvent?: (event: StreamEvent) => void;

  constructor(type: AgentType) {
    this.id = generateId();
    this.type = type;
  }

  /**
   * Initialize the agent with session context
   */
  public initialize(sessionId: string, onStreamEvent?: (event: StreamEvent) => void): void {
    this.sessionId = sessionId;
    this.onStreamEvent = onStreamEvent;
    this.status = 'idle';
    this.progress = 0;
  }

  /**
   * Main execution method - must be implemented by subclasses
   */
  public abstract execute(task: AgentTask): Promise<AgentResult>;

  /**
   * Validate results before returning - can be overridden by subclasses
   */
  public async validate(result: AgentResult): Promise<boolean> {
    // Basic validation - check if we have findings
    if (!result.findings || result.findings.length === 0) {
      return false;
    }

    // Check if all findings have required fields
    return result.findings.every(finding => 
      finding.content && 
      finding.confidence >= 0 && 
      finding.confidence <= 1 &&
      finding.sources.length > 0
    );
  }

  /**
   * Process a task with status management
   */
  public async processTask(task: AgentTask): Promise<AgentResult> {
    try {
      this.status = 'working';
      this.currentTask = task.query;
      this.progress = 0;
      
      await this.reportProgress(10, `Starting task: ${task.query}`);
      
      // Execute the task
      const result = await this.execute(task);
      
      // Validate the result
      const isValid = await this.validate(result);
      if (!isValid) {
        throw new Error('Agent result validation failed');
      }
      
      this.status = 'completed';
      this.progress = 100;
      await this.reportProgress(100, 'Task completed');
      
      return result;
    } catch (error) {
      this.status = 'failed';
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      await this.streamEvent({
        type: StreamEventType.ERROR,
        sessionId: this.sessionId,
        timestamp: new Date(),
        data: {
          agentId: this.id,
          error: errorMessage
        }
      });
      
      return {
        agentId: this.id,
        taskId: task.id,
        success: false,
        findings: [],
        errors: [errorMessage]
      };
    }
  }

  /**
   * Report progress to the orchestrator
   */
  protected async reportProgress(progress: number, message?: string): Promise<void> {
    this.progress = progress;
    
    await this.streamEvent({
      type: StreamEventType.AGENT_PROGRESS,
      sessionId: this.sessionId,
      timestamp: new Date(),
      data: {
        agentId: this.id,
        agentType: this.type,
        progress,
        message,
        currentTask: this.currentTask
      }
    });
  }

  /**
   * Stream a finding as it's discovered
   */
  protected async reportFinding(finding: Finding): Promise<void> {
    await this.streamEvent({
      type: StreamEventType.FINDING,
      sessionId: this.sessionId,
      timestamp: new Date(),
      data: {
        agentId: this.id,
        agentType: this.type,
        finding
      }
    });
  }

  /**
   * Stream an event
   */
  protected async streamEvent(event: StreamEvent): Promise<void> {
    if (this.onStreamEvent) {
      this.onStreamEvent(event);
    }
  }

  /**
   * Clean up resources
   */
  public async cleanup(): Promise<void> {
    this.status = 'idle';
    this.progress = 0;
    this.currentTask = undefined;
  }

  /**
   * Helper method to create a finding
   */
  protected createFinding(
    content: string,
    confidence: number,
    sources: any[],
    category: Finding['category'] = 'analysis'
  ): Finding {
    return {
      id: generateId(),
      agentId: this.id,
      content,
      confidence,
      sources,
      timestamp: new Date(),
      category,
      relevance: 0.5 // Will be calculated based on context
    };
  }

  /**
   * Calculate relevance score for a finding
   */
  protected calculateRelevance(finding: string, query: string): number {
    // Simple keyword matching for now
    const queryWords = query.toLowerCase().split(' ');
    const findingWords = finding.toLowerCase().split(' ');
    
    const matches = queryWords.filter(word => 
      findingWords.includes(word)
    ).length;
    
    return Math.min(matches / queryWords.length, 1);
  }
}