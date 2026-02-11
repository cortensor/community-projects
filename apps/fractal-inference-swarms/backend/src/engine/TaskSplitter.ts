import { v4 as uuidv4 } from 'uuid';
import { SubTask } from '../models/Task';
import { createChildLogger } from '../utils/logger';
import { config } from '../config';

const logger = createChildLogger('TaskSplitter');

interface SplitConfig {
  strategy: 'semantic' | 'equal' | 'weighted';
  swarmSize: number;
  taskDescription: string;
  taskId: string;
}

const SEMANTIC_DECOMPOSITION_PATTERNS: Record<string, string[]> = {
  analysis: [
    'Analyze the core requirements and identify key constraints',
    'Research existing approaches and best practices',
    'Evaluate potential solutions against defined criteria',
    'Synthesize findings into actionable recommendations',
    'Validate conclusions with cross-reference checks',
  ],
  development: [
    'Design the architecture and define component interfaces',
    'Implement core logic and business rules',
    'Build integration layer and external connections',
    'Develop error handling and edge case coverage',
    'Create testing strategy and validate outputs',
  ],
  research: [
    'Define research scope and identify key questions',
    'Gather primary sources and data points',
    'Analyze patterns and correlations in findings',
    'Cross-validate findings against secondary sources',
    'Compile findings into structured summary',
  ],
  creative: [
    'Explore conceptual space and ideation',
    'Develop initial framework and structure',
    'Elaborate on core themes and details',
    'Refine and polish output quality',
    'Review for coherence and consistency',
  ],
  general: [
    'Break down the problem into constituent parts',
    'Address the primary objective directly',
    'Handle secondary concerns and dependencies',
    'Validate and verify partial outputs',
    'Integrate and reconcile all partial results',
  ],
};

function detectTaskCategory(description: string): string {
  const lower = description.toLowerCase();
  const keywords: Record<string, string[]> = {
    analysis: ['analyze', 'evaluate', 'assess', 'review', 'examine', 'compare', 'benchmark'],
    development: ['build', 'implement', 'create', 'develop', 'code', 'program', 'design system'],
    research: ['research', 'investigate', 'study', 'explore', 'find out', 'discover', 'survey'],
    creative: ['write', 'compose', 'generate', 'craft', 'design', 'imagine', 'story', 'content'],
  };

  let bestCategory = 'general';
  let bestScore = 0;

  for (const [category, words] of Object.entries(keywords)) {
    const score = words.reduce((acc, word) => acc + (lower.includes(word) ? 1 : 0), 0);
    if (score > bestScore) {
      bestScore = score;
      bestCategory = category;
    }
  }

  return bestCategory;
}

function generateSubtaskDescription(
  baseDescription: string,
  pattern: string,
  index: number,
  total: number
): string {
  return `[Subtask ${index + 1}/${total}] ${pattern}\n\nContext from parent task: ${baseDescription}`;
}

function generateConstraints(index: number, total: number): string[] {
  const constraints: string[] = [
    `Part ${index + 1} of ${total} — maintain consistency with other subtask outputs`,
    'Output must be self-contained yet compatible with merge operation',
    'Include confidence assessment in output',
  ];

  if (index === 0) {
    constraints.push('Establish foundational context for subsequent subtasks');
  }
  if (index === total - 1) {
    constraints.push('Ensure coverage of any gaps from prior subtasks');
  }

  return constraints;
}

export class TaskSplitter {
  splitTask(cfg: SplitConfig): SubTask[] {
    logger.info('Splitting task', {
      taskId: cfg.taskId,
      strategy: cfg.strategy,
      swarmSize: cfg.swarmSize,
    });

    switch (cfg.strategy) {
      case 'semantic':
        return this.semanticSplit(cfg);
      case 'equal':
        return this.equalSplit(cfg);
      case 'weighted':
        return this.weightedSplit(cfg);
      default:
        return this.semanticSplit(cfg);
    }
  }

  private semanticSplit(cfg: SplitConfig): SubTask[] {
    const category = detectTaskCategory(cfg.taskDescription);
    const patterns = SEMANTIC_DECOMPOSITION_PATTERNS[category];
    const now = Date.now();

    logger.debug('Detected task category', { category, taskId: cfg.taskId });

    const subtasks: SubTask[] = [];
    for (let i = 0; i < cfg.swarmSize; i++) {
      const patternIndex = i % patterns.length;
      subtasks.push({
        id: uuidv4(),
        parentTaskId: cfg.taskId,
        index: i,
        description: generateSubtaskDescription(
          cfg.taskDescription,
          patterns[patternIndex],
          i,
          cfg.swarmSize
        ),
        context: `Category: ${category} | Strategy: semantic | Agent ${i + 1}/${cfg.swarmSize}`,
        constraints: generateConstraints(i, cfg.swarmSize),
        assignedAgentId: null,
        status: 'pending',
        createdAt: now,
        completedAt: null,
      });
    }

    logger.info('Task split complete', {
      taskId: cfg.taskId,
      subtaskCount: subtasks.length,
      category,
    });

    return subtasks;
  }

  private equalSplit(cfg: SplitConfig): SubTask[] {
    const now = Date.now();
    const subtasks: SubTask[] = [];

    for (let i = 0; i < cfg.swarmSize; i++) {
      subtasks.push({
        id: uuidv4(),
        parentTaskId: cfg.taskId,
        index: i,
        description: `[Equal Split ${i + 1}/${cfg.swarmSize}] Process segment ${i + 1} of the task: ${cfg.taskDescription}`,
        context: `Strategy: equal | Segment ${i + 1}/${cfg.swarmSize}`,
        constraints: [
          `Handle exactly 1/${cfg.swarmSize} of the total workload`,
          'Maintain output format consistency',
          'Include segment boundaries in output',
        ],
        assignedAgentId: null,
        status: 'pending',
        createdAt: now,
        completedAt: null,
      });
    }

    return subtasks;
  }

  private weightedSplit(cfg: SplitConfig): SubTask[] {
    const now = Date.now();
    const weights = this.calculateWeights(cfg.swarmSize);
    const subtasks: SubTask[] = [];

    for (let i = 0; i < cfg.swarmSize; i++) {
      subtasks.push({
        id: uuidv4(),
        parentTaskId: cfg.taskId,
        index: i,
        description: `[Weighted Split ${i + 1}/${cfg.swarmSize}, weight: ${weights[i].toFixed(2)}] ${cfg.taskDescription}`,
        context: `Strategy: weighted | Weight: ${weights[i].toFixed(2)} | Priority rank: ${i + 1}`,
        constraints: [
          `Allocated weight: ${(weights[i] * 100).toFixed(1)}% of total effort`,
          'Higher weight subtasks should produce more detailed output',
          'Include weight-proportional depth of analysis',
        ],
        assignedAgentId: null,
        status: 'pending',
        createdAt: now,
        completedAt: null,
      });
    }

    return subtasks;
  }

  private calculateWeights(size: number): number[] {
    const raw = Array.from({ length: size }, (_, i) => size - i);
    const sum = raw.reduce((a, b) => a + b, 0);
    return raw.map((w) => w / sum);
  }
}

export const taskSplitter = new TaskSplitter();