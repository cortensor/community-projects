import { v4 as uuidv4 } from 'uuid';
import { Agent, AgentResult, InferenceMetadata } from '../models/AgentResult';
import { SubTask } from '../models/Task';
import { createChildLogger } from '../utils/logger';
import { eventBus } from '../utils/EventBus';

const logger = createChildLogger('SwarmAgent');

const AGENT_NAMES = [
  'Nexus', 'Cipher', 'Prism', 'Vortex', 'Echo',
  'Quasar', 'Helix', 'Flux', 'Zenith', 'Pulse',
  'Orbit', 'Shard', 'Nova', 'Drift', 'Apex',
  'Arc', 'Blaze', 'Core', 'Delta', 'Enigma',
];

const INFERENCE_TEMPLATES: Record<string, string[]> = {
  analysis: [
    'After comprehensive analysis of the given parameters, the primary finding indicates that {topic} demonstrates significant correlation with {factor}. The data suggests a {confidence_level} confidence level in this assessment. Key metrics show {metric1} trending {direction} while {metric2} maintains stability. Recommendation: {action}.',
    'Systematic evaluation reveals {count} critical factors influencing {topic}. Primary driver: {factor} (impact coefficient: {coeff}). Secondary influences include environmental variables and temporal dynamics. Confidence in assessment: {confidence_level}. Risk profile: {risk}.',
  ],
  development: [
    'Architecture proposal for {topic}: Implement a {pattern} pattern with {layer_count} layers. Core module handles {responsibility1}, while auxiliary services manage {responsibility2}. Estimated complexity: O({complexity}). Scalability factor: {scale_factor}x. Implementation confidence: {confidence_level}.',
    'Technical specification for {topic}: Utilize {technology} framework with {approach} methodology. Module decomposition yields {module_count} independent components. Integration points: {integration_count}. Test coverage target: {coverage}%. Delivery confidence: {confidence_level}.',
  ],
  research: [
    'Research findings on {topic}: Literature review of {source_count} sources reveals consensus on {finding}. Divergent viewpoints exist regarding {controversy}. Meta-analysis suggests {conclusion} with p-value < {p_value}. Recommendation for further investigation: {recommendation}.',
    'Investigation into {topic} yields {finding_count} significant findings. Primary conclusion: {conclusion}. Supporting evidence spans {evidence_count} independent sources. Methodology: {methodology}. Confidence interval: {ci_lower}–{ci_upper}. Research quality score: {confidence_level}.',
  ],
  general: [
    'Processing subtask for {topic}: Generated output addresses {aspect_count} key aspects. Primary output covers {primary_aspect} with {depth} depth of analysis. Secondary considerations include {secondary_aspects}. Output reliability: {confidence_level}. Compute efficiency: {efficiency}%.',
    'Task completion for {topic}: Addressed all {constraint_count} constraints. Output quality score: {quality_score}/10. Key deliverable: {deliverable}. Verification status: {verification}. Processing iterations: {iterations}. Final confidence: {confidence_level}.',
  ],
};

function generateInferenceOutput(subtask: SubTask, iterations: number): string {
  const categoryKeywords: Record<string, string[]> = {
    analysis: ['analyze', 'evaluate', 'assess', 'review', 'examine', 'compare'],
    development: ['build', 'implement', 'create', 'develop', 'code', 'design'],
    research: ['research', 'investigate', 'study', 'explore', 'find', 'discover'],
  };

  let category = 'general';
  const lower = subtask.description.toLowerCase();
  for (const [cat, words] of Object.entries(categoryKeywords)) {
    if (words.some((w) => lower.includes(w))) {
      category = cat;
      break;
    }
  }

  const templates = INFERENCE_TEMPLATES[category];
  const template = templates[Math.floor(Math.random() * templates.length)];
  const confidence = (0.6 + Math.random() * 0.35).toFixed(4);

  const replacements: Record<string, string> = {
    topic: subtask.description.slice(0, 60),
    factor: 'multi-dimensional parameter space',
    confidence_level: `${(parseFloat(confidence) * 100).toFixed(1)}%`,
    metric1: 'throughput',
    metric2: 'latency',
    direction: Math.random() > 0.5 ? 'upward' : 'stabilizing',
    action: 'proceed with optimized configuration',
    count: String(Math.floor(3 + Math.random() * 8)),
    coeff: (Math.random() * 0.9 + 0.1).toFixed(3),
    risk: Math.random() > 0.5 ? 'moderate' : 'low',
    pattern: ['microservice', 'event-driven', 'layered', 'hexagonal'][Math.floor(Math.random() * 4)],
    layer_count: String(Math.floor(3 + Math.random() * 4)),
    responsibility1: 'core business logic',
    responsibility2: 'cross-cutting concerns',
    complexity: ['n log n', 'n', 'n²', 'log n'][Math.floor(Math.random() * 4)],
    scale_factor: String(Math.floor(2 + Math.random() * 10)),
    technology: ['distributed', 'reactive', 'modular', 'cloud-native'][Math.floor(Math.random() * 4)],
    approach: ['iterative', 'incremental', 'adaptive'][Math.floor(Math.random() * 3)],
    module_count: String(Math.floor(4 + Math.random() * 12)),
    integration_count: String(Math.floor(2 + Math.random() * 6)),
    coverage: String(Math.floor(80 + Math.random() * 20)),
    source_count: String(Math.floor(10 + Math.random() * 50)),
    finding: 'convergent optimization patterns',
    controversy: 'scalability trade-offs',
    conclusion: 'statistically significant improvement',
    p_value: (Math.random() * 0.05).toFixed(4),
    recommendation: 'expand sample size and extend temporal range',
    finding_count: String(Math.floor(3 + Math.random() * 8)),
    evidence_count: String(Math.floor(5 + Math.random() * 20)),
    methodology: 'systematic multi-source analysis',
    ci_lower: (parseFloat(confidence) - 0.1).toFixed(2),
    ci_upper: Math.min(1, parseFloat(confidence) + 0.1).toFixed(2),
    aspect_count: String(Math.floor(3 + Math.random() * 5)),
    primary_aspect: 'core objective fulfillment',
    depth: ['thorough', 'comprehensive', 'detailed'][Math.floor(Math.random() * 3)],
    secondary_aspects: 'edge cases and boundary conditions',
    efficiency: String(Math.floor(70 + Math.random() * 30)),
    constraint_count: String(subtask.constraints.length),
    quality_score: (7 + Math.random() * 3).toFixed(1),
    deliverable: 'structured analytical output',
    verification: Math.random() > 0.3 ? 'passed' : 'partial',
    iterations: String(iterations),
  };

  let output = template;
  for (const [key, value] of Object.entries(replacements)) {
    output = output.replace(new RegExp(`\\{${key}\\}`, 'g'), value);
  }

  return output;
}

export class SwarmAgentRunner {
  async spawnAndRun(subtask: SubTask, taskId: string): Promise<{ agent: Agent; result: AgentResult }> {
    const agentId = uuidv4();
    const agentName = AGENT_NAMES[Math.floor(Math.random() * AGENT_NAMES.length)] + '-' + agentId.slice(0, 6);

    const agent: Agent = {
      id: agentId,
      taskId,
      subtaskId: subtask.id,
      name: agentName,
      status: 'initializing',
      spawnedAt: Date.now(),
      startedAt: null,
      completedAt: null,
      computeTimeMs: 0,
      memoryUsageMb: 0,
      inferenceIterations: 0,
    };

    logger.info('Agent spawned', { agentId, name: agentName, subtaskId: subtask.id });
    eventBus.emitSwarmEvent('agent:spawned', taskId, { agent });

    await this.simulateBootup();
    agent.status = 'running';
    agent.startedAt = Date.now();
    eventBus.emitSwarmEvent('agent:started', taskId, { agent });

    try {
      const result = await this.runInference(agent, subtask, taskId);
      agent.status = 'completed';
      agent.completedAt = Date.now();
      agent.computeTimeMs = agent.completedAt - agent.startedAt;

      logger.info('Agent completed', {
        agentId,
        name: agentName,
        computeTimeMs: agent.computeTimeMs,
        confidence: result.confidence,
      });

      eventBus.emitSwarmEvent('agent:completed', taskId, { agent, result });
      return { agent, result };
    } catch (error) {
      agent.status = 'failed';
      agent.completedAt = Date.now();
      agent.computeTimeMs = agent.completedAt - (agent.startedAt || agent.spawnedAt);

      logger.error('Agent failed', { agentId, error: (error as Error).message });
      eventBus.emitSwarmEvent('agent:failed', taskId, { agent, error: (error as Error).message });
      throw error;
    }
  }

  private async runInference(agent: Agent, subtask: SubTask, taskId: string): Promise<AgentResult> {
    const iterations = 3 + Math.floor(Math.random() * 8);
    const intermediateOutputs: string[] = [];

    for (let i = 0; i < iterations; i++) {
      const iterationDelay = 100 + Math.random() * 400;
      await new Promise((resolve) => setTimeout(resolve, iterationDelay));

      const progress = ((i + 1) / iterations) * 100;
      agent.inferenceIterations = i + 1;
      agent.memoryUsageMb = 128 + Math.random() * 384;

      intermediateOutputs.push(`Iteration ${i + 1}: Processing ${progress.toFixed(0)}% complete`);

      eventBus.emitSwarmEvent('agent:progress', taskId, {
        agentId: agent.id,
        progress,
        iteration: i + 1,
        totalIterations: iterations,
        memoryUsageMb: agent.memoryUsageMb,
      });
    }

    const output = generateInferenceOutput(subtask, iterations);
    const confidence = 0.55 + Math.random() * 0.4;
    const reliability = 0.6 + Math.random() * 0.35;
    const convergenceReached = confidence > 0.7 && reliability > 0.7;

    const metadata: InferenceMetadata = {
      modelVersion: `fractal-swarm-v${(1 + Math.random()).toFixed(1)}`,
      temperature: 0.3 + Math.random() * 0.5,
      topP: 0.85 + Math.random() * 0.14,
      iterationsRun: iterations,
      convergenceReached,
      intermediateOutputs,
    };

    const computeTimeMs = Date.now() - (agent.startedAt || Date.now());

    return {
      id: uuidv4(),
      agentId: agent.id,
      taskId,
      subtaskId: subtask.id,
      output,
      confidence: Math.round(confidence * 10000) / 10000,
      computeTimeMs,
      reliabilityScore: Math.round(reliability * 10000) / 10000,
      tokenCount: Math.floor(100 + Math.random() * 500),
      inferenceMetadata: metadata,
      createdAt: Date.now(),
    };
  }

  private simulateBootup(): Promise<void> {
    const bootTime = 200 + Math.random() * 500;
    return new Promise((resolve) => setTimeout(resolve, bootTime));
  }
}

export const swarmAgentRunner = new SwarmAgentRunner();