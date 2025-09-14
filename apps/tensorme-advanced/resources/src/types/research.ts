// Research System Type Definitions

export type AgentType = 
  | 'web_search' 
  | 'deep_analysis' 
  | 'fact_check' 
  | 'synthesis'
  | 'code_analysis';

export type ResearchStatus = 
  | 'initializing'
  | 'analyzing'
  | 'researching' 
  | 'synthesizing'
  | 'completed'
  | 'failed'
  | 'aborted';

export type AgentStatus = 
  | 'idle' 
  | 'working' 
  | 'completed' 
  | 'failed';

export type ResearchMode = 
  | 'quick'    // Single agent, fast response
  | 'standard' // Multiple agents, balanced
  | 'deep';    // All agents, comprehensive

export interface ResearchOptions {
  mode?: ResearchMode;
  maxAgents?: number;
  timeout?: number; // milliseconds
  domains?: string[];
  includeCode?: boolean;
  maxDepth?: number;
}

export interface QueryAnalysis {
  complexity: 'simple' | 'moderate' | 'complex';
  domains: string[];
  requiredAgents: AgentType[];
  estimatedTime: number; // seconds
  subQuestions: string[];
  searchTerms: string[];
}

export interface ResearchPlan {
  phases: ResearchPhase[];
  parallelizable: boolean;
  maxConcurrentAgents: number;
  totalEstimatedTime: number;
}

export interface ResearchPhase {
  phase: 'discovery' | 'deep_dive' | 'verification' | 'synthesis';
  agents: AgentType[];
  duration: number; // seconds
  dependencies?: string[]; // phase names that must complete first
}

export interface AgentTask {
  id: string;
  type: 'search' | 'analyze' | 'verify' | 'synthesize';
  query: string;
  context?: string;
  previousFindings?: Finding[];
  constraints?: {
    maxResults?: number;
    timeLimit?: number;
    domains?: string[];
  };
}

export interface AgentResult {
  agentId: string;
  taskId: string;
  success: boolean;
  findings: Finding[];
  errors?: string[];
  metadata?: {
    sourcesChecked?: number;
    confidence?: number;
    processingTime?: number;
  };
}

export interface Finding {
  id: string;
  agentId: string;
  content: string;
  confidence: number; // 0-1
  sources: Source[];
  timestamp: Date;
  category: 'fact' | 'opinion' | 'analysis' | 'statistic' | 'quote';
  relevance: number; // 0-1
  tags?: string[];
}

export interface Source {
  title: string;
  url?: string;
  author?: string;
  date?: Date;
  credibility: number; // 0-1
  type: 'academic' | 'news' | 'blog' | 'social' | 'official' | 'unknown';
}

export interface ResearchSession {
  id: string;
  query: string;
  options: ResearchOptions;
  status: ResearchStatus;
  startTime: Date;
  endTime?: Date;
  analysis?: QueryAnalysis;
  plan?: ResearchPlan;
  agents: Map<string, AgentState>;
  findings: Finding[];
  finalReport?: ResearchReport;
  errors: Error[];
}

export interface AgentState {
  agentId: string;
  type: AgentType;
  status: AgentStatus;
  progress: number; // 0-100
  currentTask?: string;
  tasksCompleted: number;
  totalTasks: number;
  results: AgentResult[];
  errors: Error[];
  startTime?: Date;
  endTime?: Date;
}

export interface ResearchReport {
  sessionId: string;
  query: string;
  summary: string;
  detailedFindings: Section[];
  sources: Source[];
  confidence: number;
  limitations: string[];
  furtherResearch: string[];
  metadata: {
    totalAgents: number;
    totalSources: number;
    processingTime: number;
    timestamp: Date;
  };
}

export interface Section {
  title: string;
  content: string;
  findings: Finding[];
  subsections?: Section[];
}

// Stream Event Types
export enum StreamEventType {
  SESSION_START = 'session_start',
  ANALYSIS_COMPLETE = 'analysis_complete',
  AGENT_SPAWN = 'agent_spawn',
  AGENT_PROGRESS = 'agent_progress',
  FINDING = 'finding',
  AGENT_COMPLETE = 'agent_complete',
  SYNTHESIS_START = 'synthesis_start',
  FINAL_REPORT = 'final_report',
  SESSION_COMPLETE = 'session_complete',
  SESSION_ABORTED = 'session_aborted',
  ERROR = 'error'
}

export interface StreamEvent {
  type: StreamEventType;
  sessionId: string;
  timestamp: Date;
  data: any;
}