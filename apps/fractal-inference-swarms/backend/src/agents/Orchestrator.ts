import { v4 as uuidv4 } from 'uuid';
import { Task, TaskCreateRequest, createTask, MergedOutput } from '../models/Task';
import { Agent, AgentResult, ScoredResult, RewardTransaction, SwarmSession, SwarmMetrics } from '../models/AgentResult';
import { taskSplitter } from '../engine/TaskSplitter';
import { scoringEngine } from '../engine/ScoringEngine';
import { rewardEngine } from '../engine/RewardEngine';
import { mergeEngine, MergeStrategy } from '../engine/MergeEngine';
import { swarmAgentRunner } from './SwarmAgent';
import { x402Engine } from '../payments/X402Mock';
import { eventBus } from '../utils/EventBus';
import { config } from '../config';
import { createChildLogger } from '../utils/logger';

const logger = createChildLogger('Orchestrator');

const ORCHESTRATOR_WALLET = 'orchestrator-treasury-0x000';

export class Orchestrator {
  private tasks: Map<string, Task> = new Map();
  private sessions: Map<string, SwarmSession> = new Map();
  private allRewards: RewardTransaction[] = [];
  private startTime: number = Date.now();
  private totalAgentsSpawned: number = 0;
  private totalTasksCompleted: number = 0;
  private totalTokensDistributed: number = 0;

  async submitTask(request: TaskCreateRequest): Promise<Task> {
    const task = createTask(request, config.orchestrator.defaultSwarmSize);
    this.tasks.set(task.id, task);

    logger.info('Task submitted', {
      taskId: task.id,
      title: task.title,
      swarmSize: task.swarmSize,
    });

    eventBus.emitSwarmEvent('task:created', task.id, { task });

    this.executeTaskPipeline(task).catch((error) => {
      logger.error('Task pipeline failed', {
        taskId: task.id,
        error: (error as Error).message,
      });
      task.status = 'failed';
      task.errorMessage = (error as Error).message;
      task.updatedAt = Date.now();
      eventBus.emitSwarmEvent('task:failed', task.id, { task, error: (error as Error).message });
    });

    return task;
  }

  private async executeTaskPipeline(task: Task): Promise<void> {
    const pipelineStart = Date.now();

    // Phase 1: Split task
    task.status = 'splitting';
    task.updatedAt = Date.now();
    eventBus.emitSwarmEvent('task:splitting', task.id, { task });

    const subtasks = taskSplitter.splitTask({
      strategy: config.orchestrator.taskSplitStrategy,
      swarmSize: task.swarmSize,
      taskDescription: task.description,
      taskId: task.id,
    });

    task.subtasks = subtasks;
    task.updatedAt = Date.now();
    eventBus.emitSwarmEvent('task:subtasks_ready', task.id, { task, subtasks });

    // Phase 2: Create swarm session
    const session: SwarmSession = {
      id: uuidv4(),
      taskId: task.id,
      agents: [],
      results: [],
      scoredResults: [],
      rewards: [],
      status: 'active',
      startedAt: Date.now(),
      completedAt: null,
      totalTokensDistributed: 0,
    };
    this.sessions.set(session.id, session);

    // Phase 3: Spawn agents and run inference
    task.status = 'spawning_agents';
    task.updatedAt = Date.now();
    eventBus.emitSwarmEvent('task:agents_spawning', task.id, { task, sessionId: session.id });

    const agentPromises = subtasks.map(async (subtask) => {
      try {
        subtask.status = 'assigned';
        const { agent, result } = await swarmAgentRunner.spawnAndRun(subtask, task.id);
        subtask.assignedAgentId = agent.id;
        subtask.status = 'completed';
        subtask.completedAt = Date.now();
        session.agents.push(agent);
        session.results.push(result);
        this.totalAgentsSpawned++;
        return { agent, result, success: true as const };
      } catch (error) {
        subtask.status = 'failed';
        logger.error('Agent execution failed for subtask', {
          subtaskId: subtask.id,
          error: (error as Error).message,
        });
        return { success: false as const, error: (error as Error).message };
      }
    });

    task.status = 'inference_running';
    task.updatedAt = Date.now();
    eventBus.emitSwarmEvent('task:inference_started', task.id, { task });

    const agentResults = await Promise.all(agentPromises);
    const successfulResults = agentResults.filter(
      (r): r is { agent: Agent; result: AgentResult; success: true } => r.success
    );

    if (successfulResults.length === 0) {
      throw new Error('All agents failed — no results to score');
    }

    eventBus.emitSwarmEvent('task:inference_complete', task.id, {
      task,
      resultCount: successfulResults.length,
      failedCount: agentResults.length - successfulResults.length,
    });

    // Phase 4: Score results
    task.status = 'scoring';
    task.updatedAt = Date.now();
    eventBus.emitSwarmEvent('task:scoring_started', task.id, { task });

    const scoredResults = scoringEngine.scoreResults(session.results);
    session.scoredResults = scoredResults;

    eventBus.emitSwarmEvent('task:scoring_complete', task.id, {
      task,
      scoredResults,
      topAgent: scoredResults[0],
    });

    // Phase 5: Merge and validate outputs
    task.status = 'merging';
    task.updatedAt = Date.now();
    eventBus.emitSwarmEvent('task:merging_started', task.id, { task });

    const mergeStrategy = this.selectMergeStrategy(scoredResults);
    const mergedOutput = mergeEngine.mergeResults(scoredResults, task.id, mergeStrategy);
    task.mergedOutput = mergedOutput;
    session.status = 'merging';

    eventBus.emitSwarmEvent('task:merge_complete', task.id, {
      task,
      mergedOutput,
    });

    eventBus.emitSwarmEvent('task:validation_complete', task.id, {
      task,
      validationPassed: mergedOutput.validationPassed,
      validationScore: mergedOutput.validationScore,
      validationDetails: mergedOutput.validationDetails,
    });

    // Phase 6: Distribute rewards
    task.status = 'distributing_rewards';
    task.updatedAt = Date.now();

    const rewards = rewardEngine.distributeRewards(scoredResults, task.id);
    session.rewards = rewards;

    const paymentBatch = rewards
      .filter((r) => r.tokensEarned > 0)
      .map((r) => ({
        from: ORCHESTRATOR_WALLET,
        to: `agent-wallet-${r.agentId.slice(0, 12)}`,
        amount: r.tokensEarned,
      }));

    if (paymentBatch.length > 0) {
      await x402Engine.processBatchPayments(paymentBatch);
    }

    this.allRewards.push(...rewards);
    const sessionTokens = rewards.reduce((sum, r) => sum + r.tokensEarned, 0);
    session.totalTokensDistributed = sessionTokens;
    this.totalTokensDistributed += sessionTokens;

    eventBus.emitSwarmEvent('task:rewards_distributed', task.id, {
      task,
      rewards,
      totalTokensDistributed: sessionTokens,
    });

    // Phase 7: Complete
    task.status = 'completed';
    task.completedAt = Date.now();
    task.updatedAt = Date.now();
    task.totalComputeTimeMs = Date.now() - pipelineStart;
    session.status = 'completed';
    session.completedAt = Date.now();
    this.totalTasksCompleted++;

    logger.info('Task pipeline complete', {
      taskId: task.id,
      totalTimeMs: task.totalComputeTimeMs,
      agentsUsed: session.agents.length,
      tokensDistributed: sessionTokens,
      validationPassed: mergedOutput.validationPassed,
    });

    eventBus.emitSwarmEvent('task:completed', task.id, {
      task,
      session,
      mergedOutput,
    });

    eventBus.emitSwarmEvent('metrics:updated', task.id, this.getMetrics());
  }

  private selectMergeStrategy(scoredResults: ScoredResult[]): MergeStrategy {
    if (scoredResults.length <= 2) return 'best_pick';

    const topScore = scoredResults[0].finalScore;
    const avgScore = scoredResults.reduce((s, r) => s + r.finalScore, 0) / scoredResults.length;
    const dominance = topScore / avgScore;

    if (dominance > 1.5) return 'best_pick';
    if (scoredResults.length >= 5) return 'hierarchical_merge';
    return 'weighted_consensus';
  }

  getTask(taskId: string): Task | undefined {
    return this.tasks.get(taskId);
  }

  getAllTasks(): Task[] {
    return Array.from(this.tasks.values()).sort((a, b) => b.createdAt - a.createdAt);
  }

  getSessionForTask(taskId: string): SwarmSession | undefined {
    return Array.from(this.sessions.values()).find((s) => s.taskId === taskId);
  }

  getAllSessions(): SwarmSession[] {
    return Array.from(this.sessions.values()).sort((a, b) => b.startedAt - a.startedAt);
  }

  getAgentsForTask(taskId: string): Agent[] {
    const session = this.getSessionForTask(taskId);
    return session?.agents || [];
  }

  getScoredResultsForTask(taskId: string): ScoredResult[] {
    const session = this.getSessionForTask(taskId);
    return session?.scoredResults || [];
  }

  getLedger(): RewardTransaction[] {
    return [...this.allRewards].sort((a, b) => b.timestamp - a.timestamp);
  }

  getMetrics(): SwarmMetrics {
    const sessions = this.getAllSessions();
    const completedSessions = sessions.filter((s) => s.status === 'completed');
    const activeSessions = sessions.filter((s) => s.status === 'active' || s.status === 'scoring' || s.status === 'merging');

    const avgSwarmSize =
      completedSessions.length > 0
        ? completedSessions.reduce((sum, s) => sum + s.agents.length, 0) / completedSessions.length
        : 0;

    const avgCompletionTime =
      completedSessions.length > 0
        ? completedSessions.reduce((sum, s) => sum + ((s.completedAt || 0) - s.startedAt), 0) / completedSessions.length
        : 0;

    const allResults = completedSessions.flatMap((s) => s.scoredResults);
    const avgConfidence =
      allResults.length > 0
        ? allResults.reduce((sum, r) => sum + r.confidence, 0) / allResults.length
        : 0;

    let topAgentId: string | null = null;
    let topAgentScore = 0;
    for (const result of allResults) {
      if (result.finalScore > topAgentScore) {
        topAgentScore = result.finalScore;
        topAgentId = result.agentId;
      }
    }

    return {
      totalSessions: sessions.length,
      activeSessions: activeSessions.length,
      totalAgentsSpawned: this.totalAgentsSpawned,
      totalTasksCompleted: this.totalTasksCompleted,
      totalTokensDistributed: Math.round(this.totalTokensDistributed * 100) / 100,
      averageSwarmSize: Math.round(avgSwarmSize * 100) / 100,
      averageCompletionTimeMs: Math.round(avgCompletionTime),
      averageConfidence: Math.round(avgConfidence * 10000) / 10000,
      topAgentId,
      topAgentScore: Math.round(topAgentScore * 10000) / 10000,
      uptimeMs: Date.now() - this.startTime,
    };
  }
}

export const orchestrator = new Orchestrator();