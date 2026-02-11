export type TaskStatus = 
  | 'pending'
  | 'splitting'
  | 'spawning_agents'
  | 'inference_running'
  | 'scoring'
  | 'merging'
  | 'validating'
  | 'distributing_rewards'
  | 'completed'
  | 'failed';

export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';

export interface SubTask {
  id: string;
  parentTaskId: string;
  index: number;
  description: string;
  context: string;
  constraints: string[];
  assignedAgentId: string | null;
  status: 'pending' | 'assigned' | 'running' | 'completed' | 'failed';
  createdAt: number;
  completedAt: number | null;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  priority: TaskPriority;
  status: TaskStatus;
  subtasks: SubTask[];
  swarmSize: number;
  metadata: Record<string, unknown>;
  mergedOutput: MergedOutput | null;
  createdAt: number;
  updatedAt: number;
  completedAt: number | null;
  totalComputeTimeMs: number;
  errorMessage: string | null;
}

export interface MergedOutput {
  taskId: string;
  finalOutput: string;
  contributingAgents: string[];
  mergeStrategy: 'weighted_consensus' | 'best_pick' | 'hierarchical_merge';
  validationScore: number;
  validationPassed: boolean;
  validationDetails: ValidationDetail[];
  mergedAt: number;
}

export interface ValidationDetail {
  criterion: string;
  passed: boolean;
  score: number;
  message: string;
}

export interface TaskCreateRequest {
  title: string;
  description: string;
  priority?: TaskPriority;
  swarmSize?: number;
  metadata?: Record<string, unknown>;
}

export function createTask(req: TaskCreateRequest, swarmSizeDefault: number): Task {
  const { v4: uuidv4 } = require('uuid');
  return {
    id: uuidv4(),
    title: req.title,
    description: req.description,
    priority: req.priority || 'medium',
    status: 'pending',
    subtasks: [],
    swarmSize: req.swarmSize || swarmSizeDefault,
    metadata: req.metadata || {},
    mergedOutput: null,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    completedAt: null,
    totalComputeTimeMs: 0,
    errorMessage: null,
  };
}