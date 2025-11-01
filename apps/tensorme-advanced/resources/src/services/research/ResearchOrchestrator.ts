import {
  ResearchSession,
  ResearchOptions,
  ResearchMode,
  ResearchStatus,
  QueryAnalysis,
  ResearchPlan,
  ResearchPhase,
  AgentType,
  AgentState,
  AgentTask,
  Finding,
  ResearchReport,
  StreamEvent,
  StreamEventType,
  Section,
  Source
} from '@/types/research';
import { ResearchAgent } from './agents/BaseAgent';
import { generateId } from '@/lib/utils';

export class ResearchOrchestrator {
  private sessions: Map<string, ResearchSession> = new Map();
  private agentRegistry: Map<AgentType, typeof ResearchAgent> = new Map();
  private activeAgents: Map<string, ResearchAgent> = new Map();
  private streamHandlers: Map<string, (event: StreamEvent) => void> = new Map();

  constructor() {
    this.initializeAgentRegistry();
  }

  /**
   * Register available agent types
   */
  private initializeAgentRegistry(): void {
    // Will be populated as we implement specific agents
    // this.agentRegistry.set('web_search', WebSearchAgent);
    // this.agentRegistry.set('deep_analysis', DeepAnalysisAgent);
  }

  /**
   * Register an agent type
   */
  public registerAgent(type: AgentType, agentClass: typeof ResearchAgent): void {
    this.agentRegistry.set(type, agentClass);
  }

  /**
   * Start a new research session
   */
  public async startResearch(
    query: string, 
    options: ResearchOptions = {}
  ): Promise<string> {
    const sessionId = generateId();
    
    // Create session
    const session: ResearchSession = {
      id: sessionId,
      query,
      options: {
        mode: options.mode || 'standard',
        maxAgents: options.maxAgents || 3,
        timeout: options.timeout || 60000, // 60 seconds default
        domains: options.domains || [],
        includeCode: options.includeCode || false,
        maxDepth: options.maxDepth || 2
      },
      status: 'initializing',
      startTime: new Date(),
      agents: new Map(),
      findings: [],
      errors: []
    };

    this.sessions.set(sessionId, session);

    // Start research process
    this.executeResearch(sessionId).catch(error => {
      console.error(`Research session ${sessionId} failed:`, error);
      session.status = 'failed';
      session.errors.push(error);
    });

    return sessionId;
  }

  /**
   * Main research execution flow
   */
  private async executeResearch(sessionId: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session) throw new Error('Session not found');

    try {
      // Step 1: Analyze query
      await this.streamEvent(sessionId, {
        type: StreamEventType.SESSION_START,
        sessionId,
        timestamp: new Date(),
        data: { query: session.query, options: session.options }
      });

      session.status = 'analyzing';
      const analysis = await this.analyzeQuery(session.query, session.options);
      session.analysis = analysis;

      await this.streamEvent(sessionId, {
        type: StreamEventType.ANALYSIS_COMPLETE,
        sessionId,
        timestamp: new Date(),
        data: { analysis }
      });

      // Step 2: Generate research plan
      const plan = this.generateResearchPlan(analysis, session.options);
      session.plan = plan;

      // Step 3: Execute research phases
      session.status = 'researching';
      await this.executeResearchPlan(sessionId, plan);

      // Step 4: Synthesize findings
      session.status = 'synthesizing';
      await this.streamEvent(sessionId, {
        type: StreamEventType.SYNTHESIS_START,
        sessionId,
        timestamp: new Date(),
        data: { findingsCount: session.findings.length }
      });

      const report = await this.synthesizeFindings(session);
      session.finalReport = report;

      // Step 5: Complete session
      session.status = 'completed';
      session.endTime = new Date();

      await this.streamEvent(sessionId, {
        type: StreamEventType.FINAL_REPORT,
        sessionId,
        timestamp: new Date(),
        data: { report }
      });

      await this.streamEvent(sessionId, {
        type: StreamEventType.SESSION_COMPLETE,
        sessionId,
        timestamp: new Date(),
        data: { 
          duration: session.endTime.getTime() - session.startTime.getTime(),
          findingsCount: session.findings.length,
          confidence: report.confidence
        }
      });

    } catch (error) {
      session.status = 'failed';
      session.errors.push(error as Error);
      
      await this.streamEvent(sessionId, {
        type: StreamEventType.ERROR,
        sessionId,
        timestamp: new Date(),
        data: { error: (error as Error).message }
      });
    }
  }

  /**
   * Analyze the query to determine research strategy
   */
  private async analyzeQuery(
    query: string, 
    options: ResearchOptions
  ): Promise<QueryAnalysis> {
    // For now, use a simple heuristic-based analysis
    // In production, this would use an LLM to analyze the query
    
    const words = query.split(' ').length;
    const hasComparison = /compare|versus|vs|difference/i.test(query);
    const hasTechnical = /code|implement|algorithm|technical/i.test(query);
    const hasResearch = /research|analyze|investigate|explore/i.test(query);
    
    // Determine complexity
    let complexity: QueryAnalysis['complexity'] = 'simple';
    if (words > 15 || hasComparison) complexity = 'moderate';
    if (words > 30 || (hasComparison && hasTechnical)) complexity = 'complex';
    
    // Determine required agents based on query
    const requiredAgents: AgentType[] = ['web_search'];
    
    if (complexity !== 'simple' || hasResearch) {
      requiredAgents.push('deep_analysis');
    }
    
    if (hasTechnical && options.includeCode) {
      requiredAgents.push('code_analysis');
    }
    
    if (complexity === 'complex') {
      requiredAgents.push('fact_check');
    }
    
    requiredAgents.push('synthesis'); // Always include synthesis
    
    // Generate sub-questions
    const subQuestions = this.generateSubQuestions(query);
    
    // Extract search terms
    const searchTerms = this.extractSearchTerms(query);
    
    // Estimate time based on complexity and agent count
    const estimatedTime = requiredAgents.length * 10 + 
      (complexity === 'complex' ? 20 : complexity === 'moderate' ? 10 : 5);
    
    return {
      complexity,
      domains: this.identifyDomains(query),
      requiredAgents,
      estimatedTime,
      subQuestions,
      searchTerms
    };
  }

  /**
   * Generate sub-questions for research
   */
  private generateSubQuestions(query: string): string[] {
    // Simple heuristic for now
    const questions: string[] = [];
    
    questions.push(`What are the key concepts in: ${query}?`);
    questions.push(`What are recent developments related to: ${query}?`);
    
    if (/how|why|when|where/i.test(query)) {
      questions.push(`What evidence supports answers to: ${query}?`);
    }
    
    if (/compare|versus/i.test(query)) {
      questions.push(`What are the main differences?`);
      questions.push(`What are the advantages and disadvantages?`);
    }
    
    return questions;
  }

  /**
   * Extract search terms from query
   */
  private extractSearchTerms(query: string): string[] {
    // Remove common words and extract key terms
    const stopWords = new Set(['the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 'was', 'were', 'in', 'of', 'to', 'for']);
    
    return query.toLowerCase()
      .split(/\s+/)
      .filter(word => !stopWords.has(word) && word.length > 2);
  }

  /**
   * Identify domains from query
   */
  private identifyDomains(query: string): string[] {
    const domains: string[] = [];
    
    if (/tech|computer|software|code|programming/i.test(query)) domains.push('technology');
    if (/science|research|study|experiment/i.test(query)) domains.push('science');
    if (/business|economy|market|finance/i.test(query)) domains.push('business');
    if (/health|medical|medicine|disease/i.test(query)) domains.push('health');
    if (/history|historical|past/i.test(query)) domains.push('history');
    
    if (domains.length === 0) domains.push('general');
    
    return domains;
  }

  /**
   * Generate a research plan based on analysis
   */
  private generateResearchPlan(
    analysis: QueryAnalysis,
    options: ResearchOptions
  ): ResearchPlan {
    const phases: ResearchPhase[] = [];
    
    // Discovery phase - always first
    phases.push({
      phase: 'discovery',
      agents: ['web_search'] as AgentType[],
      duration: 10
    });
    
    // Deep dive phase - if needed
    if (analysis.complexity !== 'simple') {
      phases.push({
        phase: 'deep_dive',
        agents: ['deep_analysis'] as AgentType[],
        duration: 15,
        dependencies: ['discovery']
      });
    }
    
    // Verification phase - for complex queries
    if (analysis.complexity === 'complex') {
      phases.push({
        phase: 'verification',
        agents: ['fact_check'] as AgentType[],
        duration: 10,
        dependencies: ['deep_dive']
      });
    }
    
    // Synthesis phase - always last
    phases.push({
      phase: 'synthesis',
      agents: ['synthesis'] as AgentType[],
      duration: 10,
      dependencies: analysis.complexity === 'complex' ? ['verification'] : ['deep_dive', 'discovery']
    });
    
    const totalTime = phases.reduce((sum, phase) => sum + phase.duration, 0);
    
    return {
      phases,
      parallelizable: true,
      maxConcurrentAgents: options.maxAgents || 3,
      totalEstimatedTime: totalTime
    };
  }

  /**
   * Execute the research plan
   */
  private async executeResearchPlan(
    sessionId: string,
    plan: ResearchPlan
  ): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session || !session.analysis) return;
    
    for (const phase of plan.phases) {
      // Wait for dependencies
      if (phase.dependencies) {
        // In a real implementation, we'd track phase completion
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      
      // Execute agents in this phase
      const agentPromises = phase.agents.map(agentType => 
        this.executeAgent(sessionId, agentType, session.analysis!)
      );
      
      // Wait for all agents in phase to complete
      await Promise.all(agentPromises);
    }
  }

  /**
   * Execute a single agent
   */
  private async executeAgent(
    sessionId: string,
    agentType: AgentType,
    analysis: QueryAnalysis
  ): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session) return;
    
    // Create agent instance
    const AgentClass = this.agentRegistry.get(agentType);
    if (!AgentClass) {
      console.warn(`Agent type ${agentType} not registered, skipping`);
      return;
    }
    
    const agent = new (AgentClass as any)(agentType) as ResearchAgent;
    agent.initialize(sessionId, (event) => this.handleStreamEvent(sessionId, event));
    
    // Track agent state
    const agentState: AgentState = {
      agentId: agent.id,
      type: agentType,
      status: 'idle',
      progress: 0,
      tasksCompleted: 0,
      totalTasks: analysis.subQuestions.length,
      results: [],
      errors: []
    };
    
    session.agents.set(agent.id, agentState);
    this.activeAgents.set(agent.id, agent);
    
    // Notify agent spawn
    await this.streamEvent(sessionId, {
      type: StreamEventType.AGENT_SPAWN,
      sessionId,
      timestamp: new Date(),
      data: { agentId: agent.id, agentType, totalTasks: agentState.totalTasks }
    });
    
    // Execute tasks
    for (const subQuestion of analysis.subQuestions) {
      const task: AgentTask = {
        id: generateId(),
        type: 'search',
        query: subQuestion,
        context: session.query,
        previousFindings: session.findings,
        constraints: {
          maxResults: 5,
          timeLimit: 10000,
          domains: session.options.domains
        }
      };
      
      const result = await agent.processTask(task);
      
      // Update session with findings
      if (result.success) {
        session.findings.push(...result.findings);
        agentState.results.push(result);
        agentState.tasksCompleted++;
      } else {
        agentState.errors.push(new Error(result.errors?.join(', ') || 'Unknown error'));
      }
    }
    
    // Mark agent as complete
    agentState.status = 'completed';
    agentState.endTime = new Date();
    
    await this.streamEvent(sessionId, {
      type: StreamEventType.AGENT_COMPLETE,
      sessionId,
      timestamp: new Date(),
      data: { 
        agentId: agent.id, 
        agentType,
        findingsCount: agentState.results.reduce((sum, r) => sum + r.findings.length, 0)
      }
    });
    
    // Cleanup
    await agent.cleanup();
    this.activeAgents.delete(agent.id);
  }

  /**
   * Synthesize all findings into a report
   */
  private async synthesizeFindings(session: ResearchSession): Promise<ResearchReport> {
    const findings = session.findings;
    const sources = this.extractUniqueSources(findings);
    
    // Group findings by relevance and confidence
    const highConfidenceFindings = findings.filter(f => f.confidence > 0.7);
    const mediumConfidenceFindings = findings.filter(f => f.confidence > 0.4 && f.confidence <= 0.7);
    
    // Create summary
    const summary = this.generateSummary(session.query, highConfidenceFindings);
    
    // Create detailed sections
    const sections = this.organizeIntoSections(findings);
    
    // Calculate overall confidence
    const avgConfidence = findings.reduce((sum, f) => sum + f.confidence, 0) / (findings.length || 1);
    
    // Identify limitations
    const limitations = this.identifyLimitations(session);
    
    // Suggest further research
    const furtherResearch = this.suggestFurtherResearch(session);
    
    return {
      sessionId: session.id,
      query: session.query,
      summary,
      detailedFindings: sections,
      sources,
      confidence: avgConfidence,
      limitations,
      furtherResearch,
      metadata: {
        totalAgents: session.agents.size,
        totalSources: sources.length,
        processingTime: (session.endTime?.getTime() || Date.now()) - session.startTime.getTime(),
        timestamp: new Date()
      }
    };
  }

  /**
   * Extract unique sources from findings
   */
  private extractUniqueSources(findings: Finding[]): Source[] {
    const sourceMap = new Map();
    
    findings.forEach(finding => {
      finding.sources.forEach(source => {
        const key = source.url || source.title;
        if (!sourceMap.has(key)) {
          sourceMap.set(key, source);
        }
      });
    });
    
    return Array.from(sourceMap.values());
  }

  /**
   * Generate a summary from high-confidence findings
   */
  private generateSummary(query: string, findings: Finding[]): string {
    if (findings.length === 0) {
      return `No high-confidence findings for: ${query}`;
    }
    
    // Take top 3 most relevant findings
    const topFindings = findings
      .sort((a, b) => (b.relevance * b.confidence) - (a.relevance * a.confidence))
      .slice(0, 3);
    
    return topFindings.map(f => f.content).join(' ');
  }

  /**
   * Organize findings into logical sections
   */
  private organizeIntoSections(findings: Finding[]): Section[] {
    // Group by category
    const grouped = findings.reduce((acc, finding) => {
      const category = finding.category;
      if (!acc[category]) acc[category] = [];
      acc[category].push(finding);
      return acc;
    }, {} as Record<string, Finding[]>);
    
    return Object.entries(grouped).map(([category, findings]) => ({
      title: this.formatCategoryTitle(category),
      content: this.summarizeFindings(findings),
      findings
    }));
  }

  /**
   * Format category title
   */
  private formatCategoryTitle(category: string): string {
    return category.charAt(0).toUpperCase() + category.slice(1).replace('_', ' ');
  }

  /**
   * Summarize a group of findings
   */
  private summarizeFindings(findings: Finding[]): string {
    return findings
      .slice(0, 3)
      .map(f => f.content)
      .join(' ');
  }

  /**
   * Identify limitations in the research
   */
  private identifyLimitations(session: ResearchSession): string[] {
    const limitations: string[] = [];
    
    if (session.findings.length < 5) {
      limitations.push('Limited number of sources found');
    }
    
    const avgConfidence = session.findings.reduce((sum, f) => sum + f.confidence, 0) / (session.findings.length || 1);
    if (avgConfidence < 0.6) {
      limitations.push('Low average confidence in findings');
    }
    
    if (session.errors.length > 0) {
      limitations.push(`Encountered ${session.errors.length} errors during research`);
    }
    
    return limitations;
  }

  /**
   * Suggest areas for further research
   */
  private suggestFurtherResearch(session: ResearchSession): string[] {
    const suggestions: string[] = [];
    
    // Find gaps in coverage
    if (session.analysis) {
      session.analysis.subQuestions.forEach(question => {
        const hasAnswer = session.findings.some(f => 
          f.relevance > 0.5 && f.content.toLowerCase().includes(question.toLowerCase())
        );
        
        if (!hasAnswer) {
          suggestions.push(`Further investigate: ${question}`);
        }
      });
    }
    
    return suggestions;
  }

  /**
   * Stream an event to listeners
   */
  private async streamEvent(sessionId: string, event: StreamEvent): Promise<void> {
    const handler = this.streamHandlers.get(sessionId);
    if (handler) {
      handler(event);
    }
  }

  /**
   * Handle stream events from agents
   */
  private handleStreamEvent(sessionId: string, event: StreamEvent): void {
    this.streamEvent(sessionId, event);
  }

  /**
   * Register a stream handler for a session
   */
  public onStreamEvent(sessionId: string, handler: (event: StreamEvent) => void): void {
    this.streamHandlers.set(sessionId, handler);
  }

  /**
   * Get session status
   */
  public getSessionStatus(sessionId: string): ResearchSession | null {
    return this.sessions.get(sessionId) || null;
  }

  /**
   * Abort a research session
   */
  public async abortSession(sessionId: string): Promise<boolean> {
    const session = this.sessions.get(sessionId);
    if (!session) return false;
    
    session.status = 'aborted';
    session.endTime = new Date();
    
    // Clean up active agents
    for (const [agentId, agent] of this.activeAgents) {
      if (session.agents.has(agentId)) {
        await agent.cleanup();
        this.activeAgents.delete(agentId);
      }
    }
    
    return true;
  }
}